#!/usr/bin/env python3
"""Standalone debug script: downloads 1 filing from SEC, parses it,
sends to LLM, and prints all outputs step by step.

Run with:  cd backend && .venv/bin/python -m tests.test_single_filing
"""

from __future__ import annotations

import asyncio
import json
import re
import sys

import feedparser
import httpx

# Add parent to path so we can import app modules
sys.path.insert(0, ".")

from app.services.feed_poller import FEED_URL, FORM_TO_SEGMENT, _TITLE_RE
from app.services.filing_fetcher import _get_doc_url_from_index, _download_text
from app.parsers.form_8k import parse_8k
from app.parsers.form_4 import parse_form4
from app.parsers.form_s1_s3 import parse_s1_s3
from app.parsers.form_13d_13g import parse_13d_13g
from app.parsers.form_10q import parse_10q
from app.services.alpha_engine import pre_classify
from app.config import get_settings

DIVIDER = "=" * 70


def pick_parser(form_type: str):
    base = form_type.split("/")[0].strip()
    if base in ("8-K",):
        return parse_8k, "parse_8k"
    elif base == "4":
        return parse_form4, "parse_form4"
    elif base in ("S-1", "S-3", "424B2", "424B3", "424B4", "424B5"):
        return parse_s1_s3, "parse_s1_s3"
    elif base in ("SC 13D", "SC 13G", "13D", "13G"):
        return parse_13d_13g, "parse_13d_13g"
    elif base == "10-Q":
        return parse_10q, "parse_10q"
    else:
        return None, "generic"


async def main():
    settings = get_settings()

    print(DIVIDER)
    print("SEC-Pulse Debug Test: Single Filing Pipeline")
    print(DIVIDER)

    # ── Step 1: Fetch the Atom feed ─────────────────────────────
    print("\n[Step 1] Fetching Atom feed...")
    print(f"  URL: {FEED_URL}")

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.sec_user_agent},
        http2=True,
        follow_redirects=True,
    ) as client:

        resp = await client.get(FEED_URL, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        print(f"  Total entries in feed: {len(feed.entries)}")

        if not feed.entries:
            print("  ERROR: No entries in feed!")
            return

        # ── Step 2: Parse the first entry ───────────────────────
        # Try to find an entry that matches one of our segments
        chosen = None
        for entry in feed.entries:
            tags = entry.get("tags", [])
            form_type = tags[0].get("term", "").strip() if tags else ""
            segment = FORM_TO_SEGMENT.get(form_type)
            if segment is None:
                base = form_type.split("/")[0].strip()
                segment = FORM_TO_SEGMENT.get(base)
            if segment is not None:
                chosen = entry
                break

        if chosen is None:
            print("  No entries matched our segments. Using the first entry.")
            chosen = feed.entries[0]

        # Parse fields
        tags = chosen.get("tags", [])
        form_type = tags[0].get("term", "").strip() if tags else "unknown"
        title = chosen.get("title", "")
        link = chosen.get("link", "")
        entry_id = chosen.get("id", "")
        updated = chosen.get("updated", "")

        # Company / CIK from title
        match = _TITLE_RE.match(title)
        company_name = match.group(2).strip() if match else "Unknown"
        cik = match.group(3).strip() if match else "0"

        # Accession from id
        acc_match = re.search(r"accession-number=(\S+)", entry_id)
        accession = acc_match.group(1) if acc_match else entry_id

        segment = FORM_TO_SEGMENT.get(form_type)
        if segment is None:
            base = form_type.split("/")[0].strip()
            segment = FORM_TO_SEGMENT.get(base, "unknown")

        print(f"\n[Step 2] Parsed entry fields:")
        print(f"  Title:       {title}")
        print(f"  Form Type:   {form_type}")
        print(f"  Company:     {company_name}")
        print(f"  CIK:         {cik}")
        print(f"  Accession:   {accession}")
        print(f"  Segment:     {segment}")
        print(f"  Index URL:   {link}")
        print(f"  Filed:       {updated}")

        # ── Step 3: Download the index page & find the HTM doc ──
        print(f"\n[Step 3] Downloading index page...")
        print(f"  Index URL: {link}")

        doc_url = await _get_doc_url_from_index(client, link)
        if not doc_url:
            print("  ERROR: Could not find document link on index page!")
            return

        print(f"  Found document URL: {doc_url}")

        # ── Step 4: Download the actual filing document ─────────
        print(f"\n[Step 4] Downloading filing document...")
        raw_html = await _download_text(client, doc_url)
        print(f"  Downloaded {len(raw_html):,} characters")

        # ── Step 5: Parse with form-specific parser ─────────────
        parser_fn, parser_name = pick_parser(form_type)

        print(f"\n[Step 5] Parsing with {parser_name}...")
        if parser_fn:
            raw_text, parsed_data = parser_fn(raw_html)
        else:
            raw_text = re.sub(r"<[^>]+>", " ", raw_html)
            raw_text = re.sub(r"\s+", " ", raw_text).strip()[:4000]
            parsed_data = {"form_type": form_type}

        print(f"  Extracted text length: {len(raw_text):,} chars")
        print(f"  Parsed data:")
        print(json.dumps(parsed_data, indent=4, default=str))

        # ── Step 6: Heuristic classification ────────────────────
        heuristic_signal = pre_classify(segment, parsed_data)
        print(f"\n[Step 6] Heuristic signal: {heuristic_signal}")

        # ── Step 7: Send to LLM via Ollama ──────────────────────
        print(f"\n[Step 7] Sending to LLM ({settings.ollama_model})...")
        print(f"  Ollama URL: {settings.ollama_base_url}")

        try:
            from app.services.ai_processor import summarise_filing
            ai_result = await summarise_filing(
                form_type=form_type,
                segment=segment,
                company=company_name,
                ticker=None,
                parsed_data=parsed_data,
                raw_text=raw_text,
            )
            print(f"  LLM Response:")
            print(json.dumps(ai_result, indent=4))
        except Exception as e:
            print(f"  LLM failed: {e}")
            print(f"  Falling back to heuristic...")
            ai_result = {
                "summary": raw_text[:200] + "...",
                "signal": heuristic_signal,
                "reasons": ["Heuristic (SLM unavailable)"],
            }
            print(json.dumps(ai_result, indent=4))

        # ── Summary ─────────────────────────────────────────────
        print(f"\n{DIVIDER}")
        print("FINAL RESULT")
        print(DIVIDER)
        print(f"  Company:   {company_name}")
        print(f"  Form:      {form_type}")
        print(f"  Segment:   {segment}")
        print(f"  Signal:    {ai_result.get('signal', 'neutral')}")
        print(f"  Summary:   {ai_result.get('summary', 'N/A')}")
        print(f"  Reasons:   {ai_result.get('reasons', [])}")
        print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())

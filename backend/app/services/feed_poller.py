"""Core polling loop: hits a single SEC EDGAR Atom feed every 5 seconds,
deduplicates entries, and dispatches new filings for processing."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import feedparser
import httpx
from sqlalchemy import select

from ..config import get_settings
from ..database import async_session
from ..models import FilingResponse, FilingRow, SeenFiling
from .filing_fetcher import fetch_filing_document
from .ai_processor import summarise_filing
from .alpha_engine import pre_classify

if TYPE_CHECKING:
    pass

log = logging.getLogger("secpulse.poller")

# Single unified feed URL (all form types)
FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&CIK=&type=&company=&dateb="
    "&owner=include&start=0&count=40&output=atom"
)

FORM_TO_SEGMENT: dict[str, str] = {
    "8-K": "catalyst",
    "8-K/A": "catalyst",
    "SC 13D": "whale",
    "SC 13D/A": "whale",
    "SC 13G": "whale",
    "SC 13G/A": "whale",
    "SCHEDULE 13D": "whale",
    "SCHEDULE 13D/A": "whale",
    "SCHEDULE 13G": "whale",
    "SCHEDULE 13G/A": "whale",
    "13D": "whale",
    "13D/A": "whale",
    "13G": "whale",
    "13G/A": "whale",
    "10-Q": "pulse",
    "10-Q/A": "pulse",
    "10-K": "pulse",
    "10-K/A": "pulse",
}

# Title regex: "424B2 - BofA Finance LLC (0001682472) (Filer)"
_TITLE_RE = re.compile(
    r"^([\w\-/\s]+?)\s*-\s*(.*?)\s*\((\d{10})\)\s*\((.*?)\)$"
)

# CIK → ticker mapping, loaded once at startup
_cik_ticker: dict[str, str] = {}

# In-memory set to prevent concurrent duplicate processing of the same accession
_currently_processing: set[str] = set()


async def load_cik_ticker_map(client: httpx.AsyncClient) -> None:
    """Download SEC's CIK-to-ticker JSON and populate the in-memory map."""
    global _cik_ticker
    try:
        resp = await client.get(
            "https://www.sec.gov/files/company_tickers.json",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _cik_ticker = {
            str(v["cik_str"]): v["ticker"]
            for v in data.values()
        }
        log.info("Loaded %d CIK->ticker mappings", len(_cik_ticker))
    except Exception:
        log.warning("Failed to load CIK->ticker map", exc_info=True)


def _parse_entry(entry: dict, _cik_ticker: dict = None) -> dict | None:
    """Extract structured fields from an SEC Atom feed entry."""
    _cik_ticker = _cik_ticker or {}

    # 1. Extract Form Type from Tags
    form_type = None
    tags = entry.get("tags", [])
    if tags:
        form_type = tags[0].get("term", "").strip()
    
    # 2. Parse Title for Company Name and CIK
    title = entry.get("title", "")
    match = _TITLE_RE.match(title)
    if not match:
        return None
    
    # Use title fallback if tags were empty
    if not form_type:
        form_type = match.group(1).strip()
        
    company_name = match.group(2).strip()
    cik = match.group(3).strip()

    # 3. Handle Accession Number from the ID URN
    # Input example: 'urn:tag:sec.gov,2008:accession-number=0001193125-26-055710'
    entry_id = entry.get("id", "")
    acc_match = re.search(r"accession-number=([\d-]+)", entry_id)
    accession = acc_match.group(1) if acc_match else entry_id

    # 4. Map Segment — skip form types not in active segments
    segment = FORM_TO_SEGMENT.get(form_type)
    if not segment:
        base_form = form_type.split('/')[0]
        segment = FORM_TO_SEGMENT.get(base_form)
    if not segment:
        return None

    # 5. Build Final Object
    return {
        "accession_number": accession,
        "form_type": form_type,
        "segment": segment,
        "company_name": company_name,
        "cik": cik,
        "ticker": _cik_ticker.get(cik, "..."),
        "filing_url": entry.get("link", ""),
        "filed_at": entry.get("updated", ""),
    }


async def _poll_once(client: httpx.AsyncClient) -> list[dict]:
    """Fetch the single unified Atom feed, return list of parsed entries."""
    try:
        resp = await client.get(FEED_URL, timeout=180)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        entries = []
        for entry in feed.entries:
            parsed = _parse_entry(entry)
            if parsed:
                entries.append(parsed)
        log.info("Feed returned %d entries (%d matched our segments)",
                 len(feed.entries), len(entries))
        return entries
    except Exception:
        log.warning("Feed fetch failed", exc_info=True)
        return []


async def _dedup(entries: list[dict]) -> list[dict]:
    """Filter out already-seen accession numbers. Inserts new ones."""
    if not entries:
        return []

    # Deduplicate within the batch itself
    seen_in_batch: dict[str, dict] = {}
    for e in entries:
        acc = e["accession_number"]
        if acc not in seen_in_batch:
            seen_in_batch[acc] = e
    unique_entries = list(seen_in_batch.values())
    acc_numbers = list(seen_in_batch.keys())

    async with async_session() as session:
        result = await session.execute(
            select(SeenFiling.accession_number).where(
                SeenFiling.accession_number.in_(acc_numbers)
            )
        )
        seen = {row[0] for row in result.fetchall()}

        new_entries = [e for e in unique_entries if e["accession_number"] not in seen]

        for e in new_entries:
            session.add(SeenFiling(
                accession_number=e["accession_number"],
                first_seen_at=datetime.now(timezone.utc),
            ))
        await session.commit()

    return new_entries


async def _process_filing(
    client: httpx.AsyncClient,
    entry: dict,
    broadcast_fn,
) -> None:
    """Download, parse, run AI, save, and broadcast a single filing."""
    global _currently_processing
    acc = entry["accession_number"]
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # In-memory guard: skip if already being processed concurrently
    if acc in _currently_processing:
        return
    _currently_processing.add(acc)

    try:
        # Double-check: skip if already in the filings table
        async with async_session() as session:
            existing = await session.execute(
                select(FilingRow.id).where(FilingRow.accession_number == acc)
            )
            if existing.scalar() is not None:
                return

        # Fetch the filing document using the index page URL from the feed
        raw_text, parsed_data = await fetch_filing_document(
            client, entry["filing_url"], entry["form_type"]
        )

        if not raw_text:
            log.warning("No document text for %s", acc)
            return

        # Heuristic pre-classification (numeric fallback)
        heuristic_impact = pre_classify(entry["segment"], parsed_data)

        # Broadcast "summarization in progress" to dashboard before starting AI
        if broadcast_fn:
            await broadcast_fn({
                "type": "filing_processing",
                "data": {
                    "accession_number": acc,
                    "company_name": entry["company_name"],
                    "ticker": entry.get("ticker"),
                    "form_type": entry["form_type"],
                    "segment": entry["segment"],
                    "filed_at": entry.get("filed_at", ""),
                },
            })

        # AI summarisation
        try:
            ai_result = await summarise_filing(
                form_type=entry["form_type"],
                segment=entry["segment"],
                company=entry["company_name"],
                ticker=entry.get("ticker"),
                parsed_data=parsed_data,
                raw_text=raw_text,
            )
        except Exception:
            log.warning("SLM failed for %s; using heuristic", acc, exc_info=True)
            summary = f"{entry['form_type']} filing by {entry['company_name']}"
            if entry.get("ticker"):
                summary += f" (${entry['ticker']})"
            summary += f". {raw_text[:150]}..."
            ai_result = {
                "summary": summary,
                "impact": heuristic_impact,
                "reasons": ["Heuristic classification (SLM unavailable)"],
            }

        # Persist to DB
        filed_at = entry.get("filed_at")
        if isinstance(filed_at, str):
            try:
                from dateutil.parser import parse as dtparse
                filed_at = dtparse(filed_at)
            except Exception:
                filed_at = now

        async with async_session() as session:
            row = FilingRow(
                accession_number=acc,
                form_type=entry["form_type"],
                segment=entry["segment"],
                company_name=entry["company_name"],
                cik=entry["cik"],
                ticker=entry.get("ticker"),
                filing_url=entry["filing_url"],
                filed_at=filed_at,
                discovered_at=now,
                processed_at=datetime.now(timezone.utc),
                summary=ai_result.get("summary", ""),
                signal=ai_result.get("impact", heuristic_impact),
                signal_reasons=json.dumps(ai_result.get("reasons", [])),
                raw_extract=raw_text[:settings.filing_text_max_chars],
                metadata_json=json.dumps(parsed_data, default=str),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)

        # Calculate latency
        latency_ms = None
        if isinstance(filed_at, datetime) and filed_at.tzinfo:
            latency_ms = int((datetime.now(timezone.utc) - filed_at).total_seconds() * 1000)

        # Broadcast final result via WebSocket
        filing_msg = FilingResponse(
            id=row.id,
            accession_number=row.accession_number,
            form_type=row.form_type,
            segment=row.segment,
            company_name=row.company_name,
            cik=row.cik,
            ticker=row.ticker,
            filing_url=row.filing_url,
            filed_at=row.filed_at,
            latency_ms=latency_ms,
            summary=row.summary,
            impact=row.signal,
            signal_reasons=json.loads(row.signal_reasons) if row.signal_reasons else [],
            metadata=parsed_data,
        )

        if broadcast_fn:
            await broadcast_fn({"type": "new_filing", "data": filing_msg.model_dump(mode="json")})

    finally:
        _currently_processing.discard(acc)


async def polling_loop(broadcast_fn=None) -> None:
    """Main infinite loop: poll -> dedup -> process new filings."""
    settings = get_settings()

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"},
        http2=True,
    ) as client:
        await load_cik_ticker_map(client)

        while True:
            try:
                entries = await _poll_once(client)
                new_entries = await _dedup(entries)

                if new_entries:
                    log.info("Processing %d new filings", len(new_entries))

                sem = asyncio.Semaphore(3)

                async def _process_with_sem(e):
                    async with sem:
                        await _process_filing(client, e, broadcast_fn)

                await asyncio.gather(
                    *[_process_with_sem(e) for e in new_entries],
                    return_exceptions=True,
                )
            except Exception:
                log.error("Polling cycle error", exc_info=True)

            await asyncio.sleep(settings.poll_interval_seconds)

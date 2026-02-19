"""Download filing documents from SEC EDGAR.

Flow: index page URL (from feed) -> scrape for HTM doc link -> download doc -> parse."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin

import httpx

from ..parsers.form_10q import parse_10q
from ..parsers.form_13d_13g import parse_13d_13g
from ..parsers.form_4 import parse_form4
from ..parsers.form_8k import parse_8k
from ..parsers.form_s1_s3 import parse_s1_s3

log = logging.getLogger("secpulse.fetcher")

# Throttle EDGAR document downloads
_download_sem = asyncio.Semaphore(8)
_INTER_REQUEST_DELAY = 0.1  # 100ms between requests


async def _download_text(client: httpx.AsyncClient, url: str) -> str:
    """Download a URL from EDGAR with throttling."""
    async with _download_sem:
        await asyncio.sleep(_INTER_REQUEST_DELAY)
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text

        return text


async def _get_doc_url_from_index(client: httpx.AsyncClient, index_url: str) -> str | None:
    """Download the filing index page and find the actual HTM document link.

    The index page contains a table with links to filing documents.
    Example link: <a href="/Archives/edgar/data/70858/000191870426004120/form424b2.htm">form424b2.htm</a>
    """
    try:
        html = await _download_text(client, index_url)
    except Exception:
        log.warning("Failed to download index page %s", index_url, exc_info=True)
        return None

    # Find all <a href="..."> links to filing documents.
    # Only match links inside /Archives/edgar/data/ (actual filing docs)
    # or relative filenames (no slashes = same directory as index page).
    all_links = re.findall(r'href="([^"]+)"', html, re.IGNORECASE)

    doc_links = []
    for link in all_links:
        lower = link.lower()
        # Must be a document file
        if not lower.endswith((".htm", ".html", ".xml")):
            continue
        # Skip index files
        if "-index." in lower:
            continue

        # Accept: relative filenames (no slash) like "form424b2.htm"
        # Accept: absolute paths under /Archives/edgar/data/
        # Reject: everything else (nav links like /index.htm, /cgi-bin/...)
        if "/" not in link:
            doc_links.append(link)
        elif "/Archives/edgar/data/" in link:
            doc_links.append(link)
        # else: skip (it's a nav/site link, not a filing document)

    if not doc_links:
        log.warning("No document links found on index page %s", index_url)
        return None

    # Pick the best link: prefer .htm/.html over .xml
    # Skip XSLT-rendered views (xsl* in path) and R* XBRL viewer files
    best = None
    for link in doc_links:
        lower = link.lower()
        filename = link.rsplit("/", 1)[-1]
        if filename.startswith("R") and filename[1:2].isdigit():
            continue  # Skip R1.htm, R2.htm etc
        if "/xsl" in lower:
            continue  # Skip XSLT-rendered XML views
        if filename.lower().endswith((".htm", ".html")):
            best = link
            break
    # If no .htm found, try .xml (raw XML is fine for Form 4 etc)
    if best is None:
        for link in doc_links:
            if "/xsl" not in link.lower():
                best = link
                break
    if best is None and doc_links:
        best = doc_links[0]

    # Resolve relative URLs
    if best.startswith("/"):
        best = f"https://www.sec.gov{best}"
    elif not best.startswith("http"):
        best = urljoin(index_url, best)

    log.debug("Index %s -> doc %s", index_url, best)

    def get_raw_url(url):
        """Converts a SEC IX Viewer URL to a raw data URL."""
        if "/ix?doc=" in url:
            return "https://www.sec.gov" + url.split("/ix?doc=")[1]
        return url

    best = get_raw_url(best)
    
    return best


async def fetch_filing_document(
    client: httpx.AsyncClient,
    index_url: str,
    form_type: str,
) -> tuple[str, dict]:
    """Download and parse a filing.

    Args:
        client: HTTP client
        index_url: URL of the filing index page (from the Atom feed entry)
        form_type: SEC form type (e.g. '8-K', '4', 'S-3')

    Returns:
        (raw_text, parsed_data)
    """
    doc_url = await _get_doc_url_from_index(client, index_url)
    if not doc_url:
        return ("", {})

    try:
        raw = await _download_text(client, doc_url)
    except Exception:
        log.warning("Failed to download document %s", doc_url, exc_info=True)
        return ("", {})

    # Route to the appropriate parser
    base_form = form_type.split("/")[0].strip()
    log.info("Parsing form %s with base type %s", form_type, base_form)

    if base_form in ("8-K",):
        return parse_8k(raw)
    elif base_form == "4":
        return parse_form4(raw)
    elif base_form in ("S-1", "S-3", "424B2", "424B3", "424B4", "424B5"):
        return parse_s1_s3(raw)
    elif base_form in ("SC 13D", "SC 13G", "13D", "13G", "SCHEDULE 13G", "SCHEDULE 13D"):
        return parse_13d_13g(raw)
    elif base_form == "10-Q":
        return parse_10q(raw)
    else:
        # Generic: strip HTML tags
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return (text, {"form_type": form_type})

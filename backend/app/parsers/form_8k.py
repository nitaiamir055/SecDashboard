"""Parser for SEC Form 8-K: extract item codes and event context."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Map 8-K item codes to event descriptions
ITEM_MAP: dict[str, str] = {
    "1.01": "Entry into a Material Definitive Agreement",
    "1.02": "Termination of a Material Definitive Agreement",
    "1.03": "Bankruptcy or Receivership",
    "2.01": "Completion of Acquisition or Disposition of Assets",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of a Direct Financial Obligation",
    "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
    "2.05": "Costs Associated with Exit or Disposal Activities",
    "2.06": "Material Impairments",
    "3.01": "Notice of Delisting or Failure to Satisfy Listing Standard",
    "3.02": "Unregistered Sales of Equity Securities",
    "3.03": "Material Modification to Rights of Security Holders",
    "4.01": "Changes in Registrant's Certifying Accountant",
    "4.02": "Non-Reliance on Previously Issued Financial Statements",
    "5.01": "Changes in Control of Registrant",
    "5.02": "Departure of Directors or Certain Officers; Appointment of Certain Officers",
    "5.03": "Amendments to Articles of Incorporation or Bylaws",
    "5.04": "Temporary Suspension of Trading Under Employee Benefit Plans",
    "5.05": "Amendments to the Code of Ethics",
    "5.06": "Change in Shell Company Status",
    "5.07": "Submission of Matters to a Vote of Security Holders",
    "5.08": "Shareholder Nominations",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}

BULLISH_ITEMS = {"1.01", "2.01", "2.02", "5.03", "5.07", "5.08"}
BEARISH_ITEMS = {"1.02", "1.03", "2.04", "2.05", "2.06", "3.01", "3.03", "4.02", "5.02", "5.06"}

_ITEM_RE = re.compile(r"Item\s+(\d+\.\d+)", re.IGNORECASE)


def parse_8k(raw_html: str) -> tuple[str, dict]:
    """Parse an 8-K filing HTML. Returns (text_excerpt, parsed_data)."""
    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    print(text)

    # Extract item codes
    items_found = list(set(_ITEM_RE.findall(text)))
    items_found.sort()

    print(f"Found items: {items_found}")

    item_descriptions = [
        {"code": code, "description": ITEM_MAP.get(code, "Unknown")}
        for code in items_found
    ]

    parsed_data = {
        "items": items_found,
        "item_descriptions": item_descriptions,
        "has_bullish_items": bool(set(items_found) & BULLISH_ITEMS),
        "has_bearish_items": bool(set(items_found) & BEARISH_ITEMS),
    }

    return (text, parsed_data)

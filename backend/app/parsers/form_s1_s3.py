"""Parser for SEC Forms S-1, S-3, and 424B (prospectus): detect
share offerings and potential dilution."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


_DOLLAR_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?", re.IGNORECASE)
_SHARES_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*shares", re.IGNORECASE)
_ATM_RE = re.compile(r"at[\-\s]the[\-\s]market", re.IGNORECASE)
_SHELF_RE = re.compile(r"shelf\s+registration", re.IGNORECASE)
_SECONDARY_RE = re.compile(r"secondary\s+offering", re.IGNORECASE)

PURPOSE_KEYWORDS = {
    "growth": re.compile(r"growth|expansion|acquisition|research|development|R&D", re.IGNORECASE),
    "debt": re.compile(r"debt|repay|refinanc|credit\s+facilit|indebtedness", re.IGNORECASE),
    "working_capital": re.compile(r"working\s+capital|general\s+corporate|operating\s+expenses", re.IGNORECASE),
}


def _parse_dollar_amount(match: re.Match) -> float:
    """Convert a regex match of a dollar amount to a float."""
    amount = float(match.group(1).replace(",", ""))
    multiplier = (match.group(2) or "").lower()
    if multiplier == "billion":
        amount *= 1_000_000_000
    elif multiplier == "million":
        amount *= 1_000_000
    elif multiplier == "thousand":
        amount *= 1_000
    return amount


def parse_s1_s3(raw_html: str) -> tuple[str, dict]:
    """Parse an S-1/S-3/424B filing. Returns (text_excerpt, parsed_data)."""
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    # Extract offering amounts from full text
    dollar_matches = list(_DOLLAR_RE.finditer(text))
    amounts = [_parse_dollar_amount(m) for m in dollar_matches]
    max_offering = max(amounts) if amounts else None

    # Extract share counts
    share_matches = _SHARES_RE.findall(text)
    shares = [float(s.replace(",", "")) for s in share_matches]
    max_shares = max(shares) if shares else None

    # Detect offering type (check first 10k chars where cover page info lives)
    is_atm = bool(_ATM_RE.search(text[:10000]))
    is_shelf = bool(_SHELF_RE.search(text[:10000]))
    is_secondary = bool(_SECONDARY_RE.search(text[:10000]))

    offering_type = "unknown"
    if is_atm:
        offering_type = "ATM (at-the-market)"
    elif is_shelf:
        offering_type = "shelf registration"
    elif is_secondary:
        offering_type = "secondary offering"
    else:
        offering_type = "firm commitment"

    # Detect use of proceeds
    purposes = []
    for purpose, pattern in PURPOSE_KEYWORDS.items():
        if pattern.search(text):
            purposes.append(purpose)

    parsed_data = {
        "max_offering_amount": max_offering,
        "proposed_shares": max_shares,
        "offering_type": offering_type,
        "is_atm": is_atm,
        "is_shelf": is_shelf,
        "use_of_proceeds": purposes if purposes else ["unspecified"],
    }

    return (text[:20000], parsed_data)

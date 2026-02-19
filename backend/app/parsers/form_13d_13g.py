"""Parser for SEC Schedule 13D / 13G: institutional ownership and activism."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


_PERCENT_RE = re.compile(r"(\d+\.?\d*)\s*%", re.IGNORECASE)
_ACTIVISM_KEYWORDS = re.compile(
    r"board\s+seat|board\s+representation|strategic\s+alternative|"
    r"change\s+in\s+control|extraordinary\s+transaction|merger|"
    r"proxy\s+contest|replace\s+management|special\s+meeting",
    re.IGNORECASE,
)
_PASSIVE_KEYWORDS = re.compile(
    r"investment\s+purposes?\s+only|passive\s+invest|ordinary\s+course",
    re.IGNORECASE,
)


def parse_13d_13g(raw_html: str) -> tuple[str, dict]:
    """Parse a 13D/13G filing. Returns (text_excerpt, parsed_data)."""
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    # Determine if 13D or 13G from the text
    is_13d = bool(re.search(r"schedule\s+13D", text[:2000], re.IGNORECASE))
    form_subtype = "13D" if is_13d else "13G"

    # Extract percentage ownership (look for "percent of class" context)
    percent_matches = _PERCENT_RE.findall(text[:5000])
    percentages = [float(p) for p in percent_matches if 0 < float(p) <= 100]
    # The ownership % is typically the largest percentage under 100
    ownership_pct = max(percentages) if percentages else None

    # Look for the reporting person name — typically in ITEM 2 or near "NAME OF REPORTING"
    filer_name = "Unknown"
    name_match = re.search(
        r"(?:name\s+of\s+reporting\s+person|filed\s+by)[:\s]*([A-Z][\w\s,.'&-]{3,60})",
        text[:3000],
        re.IGNORECASE,
    )
    if name_match:
        filer_name = name_match.group(1).strip()

    # Detect activism vs. passive intent
    has_activism = bool(_ACTIVISM_KEYWORDS.search(text))
    has_passive = bool(_PASSIVE_KEYWORDS.search(text))

    if is_13d and has_activism:
        strategy = "activist"
    elif has_passive:
        strategy = "passive"
    elif is_13d:
        strategy = "potentially activist"
    else:
        strategy = "passive"

    # Extract Item 4 (Purpose of Transaction) context
    item4_match = re.search(r"item\s*4[^:]*[:.]?\s*(.*?)(?:item\s*5|$)", text, re.IGNORECASE | re.DOTALL)
    purpose_text = item4_match.group(1).strip()[:500] if item4_match else ""

    parsed_data = {
        "form_subtype": form_subtype,
        "filer_name": filer_name,
        "ownership_pct": ownership_pct,
        "strategy": strategy,
        "has_activism_language": has_activism,
        "purpose_excerpt": purpose_text,
    }

    return (text, parsed_data)

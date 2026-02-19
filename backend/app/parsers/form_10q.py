"""Parser for SEC Form 10-Q: quarterly financial data extraction."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


_DOLLAR_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?", re.IGNORECASE)

# Key financial metric patterns
_REVENUE_RE = re.compile(
    r"(?:total\s+)?(?:net\s+)?revenue[s]?\s*[:\s]*\$?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_NET_INCOME_RE = re.compile(
    r"net\s+(?:income|loss)\s*[:\s]*\$?\s*\(?\s*([\d,]+(?:\.\d+)?)\s*\)?",
    re.IGNORECASE,
)
_EPS_RE = re.compile(
    r"(?:basic|diluted)\s+(?:net\s+)?(?:income|loss|earnings)\s+per\s+(?:common\s+)?share\s*[:\s]*\$?\s*\(?\s*([\d.]+)\s*\)?",
    re.IGNORECASE,
)
_CASH_RE = re.compile(
    r"cash\s+and\s+cash\s+equivalents\s*[:\s]*\$?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Sentiment / risk keywords in MD&A
RISK_KEYWORDS = [
    "supply chain", "headwinds", "inflation", "recession", "uncertainty",
    "litigation", "regulatory", "cybersecurity", "impairment", "restructuring",
    "tariff", "geopolitical", "liquidity", "default", "downgrade",
]

POSITIVE_KEYWORDS = [
    "growth", "momentum", "strong demand", "record revenue", "expansion",
    "improved margin", "exceeded expectations", "tailwind", "innovation",
]


def _extract_number(text: str) -> float | None:
    """Convert a matched number string to float."""
    try:
        return float(text.replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_10q(raw_html: str) -> tuple[str, dict]:
    """Parse a 10-Q filing. Returns (text_excerpt, parsed_data)."""
    soup = BeautifulSoup(raw_html, "lxml")

    # Detect iXBRL tags (inline XBRL financial data points)
    ix_tags = soup.find_all(lambda t: t.name and t.name.startswith("ix:"))
    ixbrl_facts: dict[str, str] = {}
    for tag in ix_tags:
        name = tag.get("name")
        if name and name not in ixbrl_facts:
            ixbrl_facts[name] = tag.get_text(strip=True)

    # Clean text: remove scripts/styles, then extract readable text
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    # Extract key financial metrics from full text (no length limit)
    revenue_match = _REVENUE_RE.search(text)
    revenue = _extract_number(revenue_match.group(1)) if revenue_match else None

    net_income_match = _NET_INCOME_RE.search(text)
    net_income = _extract_number(net_income_match.group(1)) if net_income_match else None

    eps_match = _EPS_RE.search(text)
    eps = _extract_number(eps_match.group(1)) if eps_match else None

    cash_match = _CASH_RE.search(text)
    cash = _extract_number(cash_match.group(1)) if cash_match else None

    # MD&A sentiment analysis (keyword frequency)
    mda_start = re.search(
        r"management.s?\s+discussion\s+and\s+analysis",
        text, re.IGNORECASE,
    )
    mda_text = text[mda_start.start():mda_start.start() + 10000] if mda_start else text[:10000]

    risk_mentions = {}
    for kw in RISK_KEYWORDS:
        count = len(re.findall(re.escape(kw), mda_text, re.IGNORECASE))
        if count > 0:
            risk_mentions[kw] = count

    positive_mentions = {}
    for kw in POSITIVE_KEYWORDS:
        count = len(re.findall(re.escape(kw), mda_text, re.IGNORECASE))
        if count > 0:
            positive_mentions[kw] = count

    top_risks = sorted(risk_mentions.items(), key=lambda x: x[1], reverse=True)[:3]

    parsed_data = {
        "revenue": revenue,
        "net_income": net_income,
        "eps": eps,
        "cash_and_equivalents": cash,
        "risk_mentions": risk_mentions,
        "positive_mentions": positive_mentions,
        "top_risk_factors": [r[0] for r in top_risks],
        "sentiment_score": len(positive_mentions) - len(risk_mentions),
        "ixbrl_detected": bool(ix_tags),
        "ixbrl_fact_count": len(ix_tags),
        "ixbrl_sample": dict(list(ixbrl_facts.items())[:10]),
    }

    return (text, parsed_data)

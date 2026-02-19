"""Rule-based heuristic pre-classifier. Runs before the SLM to provide
a fast signal. Used as a fallback if the SLM is unavailable or times out."""

from __future__ import annotations

from ..parsers.form_8k import BULLISH_ITEMS, BEARISH_ITEMS


def pre_classify(segment: str, parsed_data: dict) -> int:
    """Fast heuristic classification. Returns an integer in [-100, 100]."""

    if segment == "catalyst":
        items = set(parsed_data.get("items", []))
        if items & BEARISH_ITEMS:
            return -70
        if items & BULLISH_ITEMS:
            return 70
        return 0

    elif segment == "whale":
        form_subtype = parsed_data.get("form_subtype", "")
        strategy = parsed_data.get("strategy", "")
        ownership = parsed_data.get("ownership_pct")
        if form_subtype == "13D" and "activist" in strategy:
            return 80
        if form_subtype == "13D":
            return 60
        if ownership and ownership > 5:
            return 40
        return 0

    elif segment == "pulse":
        # Scale sentiment_score to [-100, 100]
        raw = parsed_data.get("sentiment_score", 0)
        return max(-100, min(100, raw * 20))

    return 0

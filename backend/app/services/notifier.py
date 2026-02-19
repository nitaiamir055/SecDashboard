"""Notification priority computation for filing alerts."""

from __future__ import annotations


def compute_priority(impact: int | None, form_type: str, segment: str) -> str:
    """Compute notification priority: high, medium, or low.

    High = strong non-neutral impact score (|impact| > 20).
    Medium = notable form type or segment.
    Low = routine.
    """
    if impact is not None and abs(impact) > 20:
        return "high"
    if form_type in ("8-K", "SC 13D") or segment in ("catalyst", "whale"):
        return "medium"
    return "low"

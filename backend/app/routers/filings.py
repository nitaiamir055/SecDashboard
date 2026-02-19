"""REST API endpoints for querying filings and stats."""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..database import async_session
from ..models import FilingResponse, FilingRow

router = APIRouter()


@router.get("/filings", response_model=List[FilingResponse])
async def list_filings(
    segment: Optional[str] = Query(None, description="Filter by segment"),
    signal: Optional[str] = Query(None, description="Filter by signal"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    async with async_session() as session:
        stmt = select(FilingRow).order_by(FilingRow.filed_at.desc())

        if segment:
            stmt = stmt.where(FilingRow.segment == segment)
        if signal:
            stmt = stmt.where(FilingRow.signal == signal)

        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

    print(rows[0].__dict__ if rows else "No rows found")  # Debug print

    return [
        FilingResponse(
            id=r.id,
            accession_number=r.accession_number,
            form_type=r.form_type,
            segment=r.segment,
            company_name=r.company_name,
            cik=r.cik,
            ticker=r.ticker,
            filing_url=r.filing_url,
            filed_at=r.filed_at,
            summary=r.summary,
            impact=r.signal,
            signal_reasons=json.loads(r.signal_reasons) if r.signal_reasons else [],
            metadata=json.loads(r.metadata_json) if r.metadata_json else {},
        )
        for r in rows
    ]


@router.get("/stats")
async def get_stats():
    """Returns filing counts by segment and signal for the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    async with async_session() as session:
        # Count by segment
        seg_result = await session.execute(
            select(FilingRow.segment, func.count(FilingRow.id))
            .where(FilingRow.filed_at >= cutoff)
            .group_by(FilingRow.segment)
        )
        by_segment = dict(seg_result.fetchall())

        # Count by signal
        sig_result = await session.execute(
            select(FilingRow.signal, func.count(FilingRow.id))
            .where(FilingRow.filed_at >= cutoff)
            .group_by(FilingRow.signal)
        )
        by_signal = dict(sig_result.fetchall())

        # Total
        total_result = await session.execute(
            select(func.count(FilingRow.id))
            .where(FilingRow.filed_at >= cutoff)
        )
        total = total_result.scalar() or 0

    return {
        "period": "24h",
        "total": total,
        "by_segment": by_segment,
        "by_signal": by_signal,
    }

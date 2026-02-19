from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text

from .database import Base


# ── SQLAlchemy ORM ──────────────────────────────────────────────

class FilingRow(Base):
    __tablename__ = "filings"

    id = Column(Integer, primary_key=True)
    accession_number = Column(String, unique=True, index=True)
    form_type = Column(String, index=True)
    segment = Column(String, index=True)
    company_name = Column(String)
    cik = Column(String, index=True)
    ticker = Column(String, nullable=True)
    filing_url = Column(String)
    filed_at = Column(DateTime)
    discovered_at = Column(DateTime)
    processed_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    signal = Column(Integer, nullable=True)  # numeric impact score: -100 to 100
    signal_reasons = Column(Text, nullable=True)  # JSON list
    raw_extract = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)


class SeenFiling(Base):
    __tablename__ = "seen_filings"

    accession_number = Column(String, primary_key=True)
    first_seen_at = Column(DateTime)


# ── Pydantic response schemas ──────────────────────────────────

class FilingResponse(BaseModel):
    id: int
    accession_number: str
    form_type: str
    segment: str
    company_name: str
    cik: str
    ticker: Optional[str]
    filing_url: str
    filed_at: datetime
    latency_ms: Optional[int] = None
    summary: Optional[str]
    impact: Optional[int]  # numeric score -100 to 100
    signal_reasons: List[str] = []
    metadata: Dict = {}
    is_pending: bool = False

    class Config:
        from_attributes = True

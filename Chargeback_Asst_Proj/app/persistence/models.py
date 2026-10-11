from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.persistence.database import Base


class CaseRecord(Base):
    __tablename__ = 'cases'
    id = Column(String, primary_key=True)
    reason_code = Column(String)
    decision = Column(String)
    confidence = Column(Float)
    status = Column(String)
    case_data = Column(Text)
    payload = Column(Text)


class EvidenceRecord(Base):
    __tablename__ = 'evidence'
    id = Column(String, primary_key=True)
    case_id = Column(String)
    evidence_type = Column(String)
    source = Column(String)
    value = Column(Text)


class AuditRecord(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String)
    step = Column(String)
    status = Column(String)
    trace_id = Column(String)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    details = Column(Text)


class FeedbackRecord(Base):
    __tablename__ = 'analyst_feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False, index=True)
    original_decision = Column(String, nullable=False)
    analyst_action = Column(String, nullable=False)
    final_decision = Column(String, nullable=False)
    comment = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

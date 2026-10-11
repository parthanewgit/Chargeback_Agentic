from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.rules.reason_codes import ReasonCode
from app.schemas.evidence import Conflict, EvidenceItem, SourceDocument


class DisputeCase(BaseModel):
    case_id: str
    dispute_reason_code: Optional[ReasonCode | str] = None
    transaction_id: Optional[str] = None
    transaction_date: Optional[datetime] = None
    dispute_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    card_last4: Optional[str] = None
    dispute_description: Optional[str] = None
    merchant_evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    conflicting_fields: list[Conflict] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)

    @field_validator('dispute_reason_code', mode='before')
    @classmethod
    def normalize_reason(cls, value):
        if isinstance(value, ReasonCode):
            return value
        if value is None:
            return None
        from app.rules.reason_codes import normalize_reason_code
        normalized = normalize_reason_code(str(value))
        return normalized or value

    @property
    def evidence_types(self) -> set[str]:
        return {ev.evidence_type for ev in self.merchant_evidence}

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str = Field(..., description='Unique evidence identifier like EVID-001')
    evidence_type: str
    source: str
    field_name: Optional[str] = None
    value: Any
    timestamp: Optional[datetime] = None
    reliability: Optional[float] = None


class SourceDocument(BaseModel):
    name: str
    kind: str
    source: str
    content: str | None = None
    checksum: str | None = None


class Conflict(BaseModel):
    field: str
    values: list[dict[str, Any]] = Field(default_factory=list)

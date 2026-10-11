from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    trace_id: str
    case_id: str
    step: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    input_reference: str | None = None
    output_reference: str | None = None
    duration_ms: int | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    status: str = 'ok'
    error: str | None = None

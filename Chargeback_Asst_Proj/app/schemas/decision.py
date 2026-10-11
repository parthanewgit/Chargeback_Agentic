from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Decision(str, Enum):
    ACCEPT = 'ACCEPT'
    CONTEST = 'CONTEST'
    REQUEST_MORE_INFO = 'REQUEST_MORE_INFO'


class DecisionOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    case_id: str
    reason_code: str
    decision: Decision
    confidence: float = Field(ge=0.0, le=1.0)
    deadline_status: str
    evidence_complete: bool
    rationale: str
    citations: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    collected_evidence: list[dict[str, Any]] = Field(default_factory=list)
    requires_human_review: bool = False
    escalation_reason: Optional[str] = None
    latency: float = 0.0
    model_usage: str = 'ollama/qwen3:8b'
    llm_status: str = 'not_used'
    llm_error: Optional[str] = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    investigation_steps: list[dict[str, Any]] = Field(default_factory=list)
    tool_history: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    security_flags: list[str] = Field(default_factory=list)
    representment_letter: Optional[str] = None
    created_at: datetime | None = None

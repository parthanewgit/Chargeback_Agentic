from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DecisionExplanation(BaseModel):
    model_config = ConfigDict(extra='forbid')

    rationale: str = Field(min_length=1, max_length=2000)
    citations: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    reason_code: str | None = None
    transaction_id: str | None = None
    amount: str | None = None
    merchant_id: str | None = None


class ToolSelection(BaseModel):
    action: str
    tool_name: str | None = None
    arguments: dict | None = None
    reason: str | None = None


class EvidenceAssessment(BaseModel):
    complete: bool = False
    missing: list[str] = Field(default_factory=list)

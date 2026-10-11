from __future__ import annotations

from typing import Any, TypedDict


class DisputeAgentState(TypedDict, total=False):
    case: Any
    evidence: list[Any]
    missing_fields: list[str]
    conflicts: list[Any]
    tool_history: list[Any]
    tool_results: list[Any]
    investigation_iteration: int
    deadline_status: str | None
    evidence_complete: bool | None
    missing_required_evidence: list[str]
    preliminary_decision: str | None
    confidence: float | None
    final_decision: Any
    representment_letter: str | None
    requires_human_review: bool
    audit_events: list[Any]
    reason_code: str
    planner_context: dict[str, Any]
    plan: dict[str, Any]
    investigation_steps: list[dict[str, Any]]
    should_stop: bool

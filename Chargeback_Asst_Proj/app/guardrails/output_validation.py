from __future__ import annotations

from app.rules.rule_engine import validate_decision


def validate_final_decision(decision: str) -> bool:
    return validate_decision(decision)

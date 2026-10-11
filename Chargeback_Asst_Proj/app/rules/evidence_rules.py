from __future__ import annotations


def assess_evidence_complete(required: set[str] | list[str], present: set[str] | list[str]) -> dict:
    required_set = set(required)
    present_set = set(present)
    missing = sorted(required_set - present_set)
    return {
        'complete': not missing,
        'required': sorted(required_set),
        'present': sorted(present_set),
        'missing': missing,
    }


def calculate_confidence(evidence_completeness: float, evidence_consistency: float, rule_certainty: float, source_reliability: float, model_interpretation: float) -> float:
    confidence = (
        evidence_completeness * 0.35
        + evidence_consistency * 0.20
        + rule_certainty * 0.20
        + source_reliability * 0.15
        + model_interpretation * 0.10
    )
    return max(0.0, min(1.0, confidence))

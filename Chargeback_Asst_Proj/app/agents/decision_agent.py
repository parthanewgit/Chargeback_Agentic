from __future__ import annotations

from typing import Any

from app.rules.deadlines import DeadlineStatus
from app.rules.evidence_rules import calculate_confidence
from app.rules.rule_engine import get_rule_for_reason


class DecisionAgent:
    def decide(self, case: Any, evidence: list[Any], missing_evidence: list[str], deadline_status: str | None, reason_code: str) -> dict[str, Any]:
        try:
            rule = get_rule_for_reason(reason_code)
            required = set(rule.required_evidence)
            present = set(item.evidence_type for item in evidence)
            missing = sorted(required - present)
            evidence_complete = not missing
            if deadline_status == DeadlineStatus.EXPIRED.value:
                decision = 'ACCEPT'
            elif not evidence_complete:
                decision = 'REQUEST_MORE_INFO'
            else:
                facts = _evidence_facts(evidence)
                decision = _decide_from_facts(reason_code, facts, case)
            conflict_score = 0.2 if getattr(case, 'conflicting_fields', []) else 0.8
            reliability_values = [item.reliability for item in evidence if item.reliability is not None]
            source_reliability = sum(reliability_values) / len(reliability_values) if reliability_values else 0.6
            confidence = calculate_confidence(
                0.9 if evidence_complete else 0.4,
                conflict_score,
                0.85 if decision != 'REQUEST_MORE_INFO' else 0.55,
                source_reliability,
                0.7,
            )
            return {'decision': decision, 'confidence': confidence, 'missing_evidence': missing, 'evidence_complete': evidence_complete}
        except Exception:
            return {'decision': 'REQUEST_MORE_INFO', 'confidence': 0.2, 'missing_evidence': ['rule_configuration'], 'evidence_complete': False}


def _evidence_facts(evidence: list[Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for item in evidence:
        if isinstance(item.value, dict):
            facts.update(item.value)
        else:
            facts[item.evidence_type] = item.value
    return facts


def _decide_from_facts(reason_code: str, facts: dict[str, Any], case: Any) -> str:
    if reason_code == 'item_not_received':
        status = str(facts.get('delivery_status', '')).lower()
        if status == 'delivered' and facts.get('address_match') is True:
            return 'CONTEST'
        if status in {'not_delivered', 'lost', 'returned_to_sender'}:
            return 'ACCEPT'
        return 'REQUEST_MORE_INFO'

    if reason_code == 'fraud_card_not_present':
        auth_status = str(facts.get('authorization_status', '')).lower()
        if auth_status in {'declined', 'unauthorized', 'not_authorized'}:
            return 'ACCEPT'
        if (
            auth_status == 'approved'
            and facts.get('three_ds') is True
            and facts.get('avs_result') == 'match'
            and facts.get('cvv_result') == 'match'
        ):
            return 'CONTEST'
        return 'REQUEST_MORE_INFO'

    if reason_code == 'duplicate_processing':
        duplicate_confirmed = facts.get('duplicate_confirmed')
        if duplicate_confirmed is True:
            return 'ACCEPT'
        if duplicate_confirmed is False:
            return 'CONTEST'
        return 'REQUEST_MORE_INFO'

    if reason_code == 'credit_not_processed':
        refund_status = str(facts.get('refund_status', '')).lower()
        if refund_status in {'processed', 'settled', 'credited'}:
            return 'CONTEST'
        if refund_status in {'not_processed', 'not_found', 'failed'}:
            return 'ACCEPT'
        return 'REQUEST_MORE_INFO'

    if reason_code == 'not_as_described':
        description_matches = facts.get('description_matches')
        if description_matches is True:
            return 'CONTEST'
        if description_matches is False:
            return 'ACCEPT'
        return 'REQUEST_MORE_INFO'

    if reason_code == 'cancelled_recurring':
        cancellation_status = str(facts.get('cancellation_status', '')).lower()
        if cancellation_status in {'effective_before_charge', 'cancelled_before_transaction'}:
            return 'ACCEPT'
        if cancellation_status in {'cancelled_after_transaction', 'not_cancelled'}:
            return 'CONTEST'
        return 'REQUEST_MORE_INFO'

    return 'REQUEST_MORE_INFO'

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DecisionRuleError(ValueError):
    pass


@dataclass
class ReasonCodeRule:
    code: str
    required_evidence: list[str] = field(default_factory=list)
    optional_evidence: list[str] = field(default_factory=list)
    response_deadline_days: int = 30
    high_value_threshold: float = 1000.0


DEFAULT_RULES = {
    'fraud_card_not_present': ReasonCodeRule('fraud_card_not_present', ['transaction_record', 'authorization_result'], ['customer_history', 'merchant_profile'], 30),
    'item_not_received': ReasonCodeRule('item_not_received', ['transaction_record', 'delivery_status'], ['customer_history', 'merchant_profile'], 30),
    'duplicate_processing': ReasonCodeRule('duplicate_processing', ['transaction_record'], ['merchant_profile', 'prior_disputes'], 30),
    'credit_not_processed': ReasonCodeRule('credit_not_processed', ['transaction_record', 'refund_record'], ['merchant_profile'], 30),
    'not_as_described': ReasonCodeRule('not_as_described', ['transaction_record', 'merchant_description'], ['customer_history', 'merchant_profile'], 30),
    'cancelled_recurring': ReasonCodeRule('cancelled_recurring', ['transaction_record', 'cancellation_record'], ['customer_history', 'merchant_profile'], 30),
}


def get_rule_for_reason(reason: str) -> ReasonCodeRule:
    key = reason.lower().replace(' ', '_') if isinstance(reason, str) else str(reason)
    if key not in DEFAULT_RULES:
        raise DecisionRuleError(f'Unsupported reason code: {reason}')
    return DEFAULT_RULES[key]


def validate_decision(decision: str) -> bool:
    return decision in {'ACCEPT', 'CONTEST', 'REQUEST_MORE_INFO'}

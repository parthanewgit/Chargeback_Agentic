from __future__ import annotations

from enum import Enum
import re


class ReasonCode(str, Enum):
    FRAUD_CARD_NOT_PRESENT = 'fraud_card_not_present'
    ITEM_NOT_RECEIVED = 'item_not_received'
    DUPLICATE_PROCESSING = 'duplicate_processing'
    CREDIT_NOT_PROCESSED = 'credit_not_processed'
    NOT_AS_DESCRIBED = 'not_as_described'
    CANCELLED_RECURRING = 'cancelled_recurring'


_REASON_ALIASES = {
    'fraud_card_not_present': ReasonCode.FRAUD_CARD_NOT_PRESENT,
    'fraud cnp': ReasonCode.FRAUD_CARD_NOT_PRESENT,
    'card not present': ReasonCode.FRAUD_CARD_NOT_PRESENT,
    'item_not_received': ReasonCode.ITEM_NOT_RECEIVED,
    'item not received': ReasonCode.ITEM_NOT_RECEIVED,
    'items not received': ReasonCode.ITEM_NOT_RECEIVED,
    'goods not received': ReasonCode.ITEM_NOT_RECEIVED,
    'merchandise not received': ReasonCode.ITEM_NOT_RECEIVED,
    'inr': ReasonCode.ITEM_NOT_RECEIVED,
    'duplicate_processing': ReasonCode.DUPLICATE_PROCESSING,
    'duplicate processing': ReasonCode.DUPLICATE_PROCESSING,
    'credit_not_processed': ReasonCode.CREDIT_NOT_PROCESSED,
    'credit not processed': ReasonCode.CREDIT_NOT_PROCESSED,
    'not_as_described': ReasonCode.NOT_AS_DESCRIBED,
    'not as described': ReasonCode.NOT_AS_DESCRIBED,
    'cancelled_recurring': ReasonCode.CANCELLED_RECURRING,
    'cancelled recurring': ReasonCode.CANCELLED_RECURRING,
    'canceled recurring': ReasonCode.CANCELLED_RECURRING,
}


def normalize_reason_code(raw: str | None) -> ReasonCode | None:
    if raw is None:
        return None
    text = raw.strip().lower().replace('_', ' ')
    text = re.sub(r'\s+', ' ', text)
    alias = _REASON_ALIASES.get(text)
    if alias is not None:
        return alias
    for key, value in _REASON_ALIASES.items():
        if key in text:
            return value
    return None

import re
from typing import Any

PAN_RE = re.compile(r'\b(?:\d[ -]?){13,19}\b')
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE_RE = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b')
NAME_LABELS = {
    'case id', 'case reference', 'transaction id', 'transaction date',
    'dispute reason', 'reason code', 'dispute date', 'response deadline',
    'deadline', 'merchant id', 'customer id', 'card last', 'customer history',
    'delivery status', 'authorization result', 'refund record',
}
NAME_RE = re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b')
ADDRESS_RE = re.compile(r'(?m)\b\d{1,5}[ \t]+[A-Za-z0-9.,#-]+(?:[ \t]+[A-Za-z0-9.,#-]+){0,5}')


def mask_pii(text: str) -> str:
    masked = text
    masked = re.sub(PAN_RE, lambda m: '************' + m.group(0)[-4:], masked)
    masked = re.sub(EMAIL_RE, '<EMAIL>', masked)
    masked = re.sub(PHONE_RE, '<PHONE>', masked)
    masked = re.sub(NAME_RE, lambda match: match.group(0) if match.group(0).lower() in NAME_LABELS else '<CUSTOMER_NAME>', masked)
    masked = re.sub(ADDRESS_RE, '<ADDRESS>', masked)
    return masked


def mask_pii_data(value: Any) -> Any:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {key: mask_pii_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_pii_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_pii_data(item) for item in value)
    return value

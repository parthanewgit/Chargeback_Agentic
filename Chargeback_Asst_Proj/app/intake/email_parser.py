from __future__ import annotations

import re


def extract_email_fields(email_text: str) -> dict[str, str]:
    fields = {}
    for key, pattern in {
        'case_id': r'^\s*case(?:\s*id|\s*reference)?\s*[:#-]\s*([A-Z0-9-]+)\s*$',
        'transaction_id': r'^\s*transaction(?:\s*id|\s*reference)\s*[:#-]\s*([A-Z0-9-]+)\s*$',
        'reason_code': r'^\s*(?:dispute\s+)?reason(?:\s*code)?\s*[:#-]\s*([^\r\n]+)',
        'amount': r'^\s*(?:disputed\s+)?amount\s*[:#-]\s*(?:(?:₹|Rs\.?|INR)\s*)?([0-9,]+(?:\.[0-9]{1,2})?)(?:\s*(?:INR|Rs\.?))?\s*$',
        'currency': r'^\s*currency\s*[:#-]\s*([A-Z]{3})\s*$',
        'merchant_id': r'^\s*merchant\s*id\s*[:#-]\s*([A-Z0-9-]+)\s*$',
        'customer_id': r'^\s*customer\s*id\s*[:#-]\s*([A-Z0-9-]+)\s*$',
        'card_last4': r'^\s*card\s*(?:last\s*4|ending)\s*[:#-]?\s*(\d{4})\s*$',
        'transaction_date': r'^\s*transaction\s*date\s*[:#-]\s*([^\r\n]+)',
        'dispute_date': r'^\s*dispute\s*date\s*[:#-]\s*([^\r\n]+)',
        'response_deadline': r'^\s*(?:response\s+)?deadline\s*[:#-]\s*([^\r\n]+)',
    }.items():
        match = re.search(pattern, email_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            fields[key] = match.group(1).strip()
    if 'currency' not in fields:
        amount_line = re.search(r'^\s*(?:disputed\s+)?amount\s*[:#-].*$', email_text, flags=re.IGNORECASE | re.MULTILINE)
        if amount_line and re.search(r'₹|\bRs\.?|\bINR\b', amount_line.group(0), flags=re.IGNORECASE):
            fields['currency'] = 'INR'
    return fields

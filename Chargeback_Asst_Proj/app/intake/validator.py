from __future__ import annotations

from app.schemas.case import DisputeCase


def validate_case(case: DisputeCase) -> DisputeCase:
    case.missing_fields = []
    if not case.case_id:
        case.missing_fields.append('case_id')
    if not case.transaction_id:
        case.missing_fields.append('transaction_id')
    return case

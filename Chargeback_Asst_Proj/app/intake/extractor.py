from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any

from app.guardrails.pii_masking import mask_pii
from app.rules.reason_codes import normalize_reason_code
from app.schemas.evidence import Conflict, EvidenceItem
from app.schemas.case import DisputeCase
from app.schemas.evidence import SourceDocument
from app.intake.email_parser import extract_email_fields


def extract_case_from_inputs(
    case_id: str | None,
    pdf_text: str | None = None,
    email_text: str | None = None,
    image_summary: dict[str, Any] | None = None,
) -> DisputeCase:
    inputs = [(name, text) for name, text in (('pdf', pdf_text), ('email', email_text)) if text]
    parsed = [(source, extract_email_fields(text)) for source, text in inputs]
    conflicts: list[Conflict] = []

    def resolve(field: str, normalize=lambda value: value):
        candidates = [(source, values[field]) for source, values in parsed if values.get(field)]
        try:
            normalized = {normalize(value) for _, value in candidates}
        except (ArithmeticError, ValueError):
            conflicts.append(Conflict(field=field, values=[{'source': source, 'value': value} for source, value in candidates]))
            return None
        if len(normalized) > 1:
            conflicts.append(Conflict(field=field, values=[{'source': source, 'value': value} for source, value in candidates]))
            return None
        return candidates[0][1] if candidates else None

    extracted_case_id = resolve('case_id')
    raw_reason = resolve('reason_code', lambda value: normalize_reason_code(value) or value.strip().lower())
    raw_amount = resolve('amount', lambda value: Decimal(value.replace(',', '')))
    currency = resolve('currency', str.upper)
    if raw_amount is not None and currency is None:
        currency = 'INR'
    transaction_id = resolve('transaction_id', str.upper)
    merchant_id = resolve('merchant_id', str.upper)
    customer_id = resolve('customer_id', str.upper)
    card_last4 = resolve('card_last4')

    def parse_datetime(field: str) -> datetime | None:
        raw_value = resolve(field, _normalize_datetime)
        return _parse_datetime(raw_value) if raw_value else None

    transaction_date = parse_datetime('transaction_date')
    dispute_date = parse_datetime('dispute_date')
    response_deadline = parse_datetime('response_deadline')
    combined = '\n'.join(text for _, text in inputs)
    source_documents = [
        SourceDocument(name=f'{source}_input.txt', kind=source, source=f'{source}_upload', content=text)
        for source, text in inputs
    ]
    if image_summary:
        image_name = str(image_summary.get('filename', 'image'))
        image_content = str(image_summary.get('text', 'Image accepted; OCR/vision extraction is unavailable.'))
        source_documents.append(SourceDocument(name=image_name, kind='image', source='image_upload', content=image_content))

    case = DisputeCase(
        case_id=extracted_case_id or case_id or 'CASE-UNASSIGNED',
        dispute_reason_code=normalize_reason_code(raw_reason) if raw_reason else None,
        transaction_id=transaction_id,
        transaction_date=transaction_date,
        dispute_date=dispute_date,
        response_deadline=response_deadline,
        amount=Decimal(raw_amount.replace(',', '')) if raw_amount else None,
        currency=currency,
        merchant_id=merchant_id,
        customer_id=customer_id,
        card_last4=card_last4,
        dispute_description=mask_pii(combined)[:12000] or None,
        conflicting_fields=conflicts,
        source_documents=source_documents,
    )
    required_intake_fields = ('case_id', 'dispute_reason_code', 'transaction_id', 'amount', 'response_deadline')
    case.missing_fields = [field for field in required_intake_fields if getattr(case, field) is None]
    if not extracted_case_id and not case_id:
        case.missing_fields.append('case_id')
    return case


def merge_manual_case_fields(
    case: DisputeCase,
    *,
    case_id: str | None = None,
    transaction_id: str | None = None,
    reason_code: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    response_deadline: datetime | None = None,
    dispute_description: str | None = None,
    merchant_evidence: list[EvidenceItem] | None = None,
) -> DisputeCase:
    conflicts = list(case.conflicting_fields)

    def merge(field: str, supplied: Any, normalize=lambda value: value):
        extracted = getattr(case, field)
        if supplied is not None and extracted is not None and normalize(supplied) != normalize(extracted):
            conflicts.append(Conflict(field=field, values=[
                {'source': 'documents', 'value': str(extracted)},
                {'source': 'analyst_input', 'value': str(supplied)},
            ]))
        return supplied if supplied is not None else extracted

    if 'case_id' in case.missing_fields and case_id:
        case.case_id = case_id
    else:
        case.case_id = merge('case_id', case_id, str.upper)
    case.transaction_id = merge('transaction_id', transaction_id, str.upper)
    case.dispute_reason_code = merge(
        'dispute_reason_code',
        normalize_reason_code(reason_code) if reason_code else None,
        lambda value: str(getattr(value, 'value', value)).lower(),
    )
    case.amount = merge('amount', amount, Decimal)
    case.currency = merge('currency', currency, str.upper)
    if case.amount is not None and case.currency is None:
        case.currency = 'INR'
    case.response_deadline = merge('response_deadline', response_deadline, _normalize_datetime)
    if dispute_description:
        case.dispute_description = '\n'.join(filter(None, [case.dispute_description, mask_pii(dispute_description)]))[:12000]
    if merchant_evidence is not None:
        case.merchant_evidence = merchant_evidence
    case.conflicting_fields = conflicts
    required_intake_fields = ('case_id', 'dispute_reason_code', 'transaction_id', 'amount', 'response_deadline')
    case.missing_fields = [field for field in required_intake_fields if getattr(case, field) is None]
    return case


def _normalize_datetime(value: str) -> str:
    return value.strip().replace('Z', '+00:00')


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(_normalize_datetime(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

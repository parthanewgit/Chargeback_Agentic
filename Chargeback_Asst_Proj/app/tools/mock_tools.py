from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _simulated_failure(kwargs: dict[str, Any]) -> dict[str, str] | None:
    mode = kwargs.get('simulate_failure')
    if mode == 'timeout':
        raise TimeoutError('simulated tool timeout')
    if mode == '404':
        return {'error': 'not_found'}
    if mode == 'temporary_unavailable':
        return {'error': 'temporary_unavailable'}
    if mode == 'malformed_response':
        return {'error': 'malformed_response'}
    return None


@lru_cache(maxsize=1)
def _synthetic_records() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    data_path = Path(__file__).resolve().parents[2] / 'data'
    cases = json.loads((data_path / 'synthetic_cases.json').read_text(encoding='utf-8'))
    evidence = json.loads((data_path / 'synthetic_evidence.json').read_text(encoding='utf-8'))
    records = json.loads((data_path / 'mock_investigation_records.json').read_text(encoding='utf-8'))
    return ({case['transaction_id']: case for case in cases}, evidence, records)


def _case_by_identifier(field_name: str, identifier: str | None) -> dict[str, Any] | None:
    if identifier is None:
        return None
    cases, _, _ = _synthetic_records()
    return next((case for case in cases.values() if case.get(field_name) == identifier), None)


def _evidence_record(transaction_id: str, evidence_type: str) -> dict[str, Any] | None:
    _, evidence, _ = _synthetic_records()
    return next(
        (item['value'] for item in evidence.get(transaction_id, []) if item['evidence_type'] == evidence_type),
        None,
    )


def get_transaction(transaction_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    failure = _simulated_failure(kwargs)
    if failure:
        return failure
    if transaction_id is None:
        return {'error': 'missing_transaction_id'}
    case = _case_by_identifier('transaction_id', transaction_id)
    transaction_facts = _evidence_record(transaction_id, 'transaction_record')
    if case is None or transaction_facts is None:
        return {'error': 'not_found'}
    result = {'transaction_id': transaction_id}
    for field in ('amount', 'currency', 'merchant_id', 'customer_id'):
        if case.get(field) is not None:
            result[field] = case[field]
    result.update(transaction_facts)
    for evidence_type in ('authorization_result', 'refund_record'):
        facts = _evidence_record(transaction_id, evidence_type)
        if facts:
            result.update(facts)
    return result


def get_customer_history(customer_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    failure = _simulated_failure(kwargs)
    if failure:
        return failure
    if customer_id is None:
        return {'error': 'missing_customer_id'}
    _, _, records = _synthetic_records()
    customer = records['customers'].get(customer_id)
    return {'customer_id': customer_id, **customer} if customer else {'error': 'not_found'}


def get_delivery_status(transaction_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    failure = _simulated_failure(kwargs)
    if failure:
        return failure
    if transaction_id is None:
        return {'error': 'missing_transaction_id'}
    delivery = _evidence_record(transaction_id, 'delivery_status')
    if delivery is None:
        return {'error': 'not_found'}
    return {'transaction_id': transaction_id, **delivery}


def get_prior_disputes(merchant_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    failure = _simulated_failure(kwargs)
    if failure:
        return failure
    if merchant_id is None:
        return {'error': 'missing_merchant_id'}
    _, _, records = _synthetic_records()
    disputes = records['prior_disputes'].get(merchant_id)
    return {'merchant_id': merchant_id, **disputes} if disputes else {'error': 'not_found'}


def get_merchant_profile(merchant_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    failure = _simulated_failure(kwargs)
    if failure:
        return failure
    if merchant_id is None:
        return {'error': 'missing_merchant_id'}
    _, _, records = _synthetic_records()
    merchant = records['merchants'].get(merchant_id)
    return {'merchant_id': merchant_id, **merchant} if merchant else {'error': 'not_found'}

from __future__ import annotations

from typing import Any

EVIDENCE_TOOL_MAP = {
    'transaction_record': ('get_transaction', 'transaction_id'),
    'authorization_result': ('get_transaction', 'transaction_id'),
    'refund_record': ('get_transaction', 'transaction_id'),
    'delivery_status': ('get_delivery_status', 'transaction_id'),
    'customer_history': ('get_customer_history', 'customer_id'),
    'prior_disputes': ('get_prior_disputes', 'merchant_id'),
    'merchant_profile': ('get_merchant_profile', 'merchant_id'),
    'merchant_description': ('get_merchant_profile', 'merchant_id'),
    'cancellation_record': ('get_customer_history', 'customer_id'),
}

EVIDENCE_PRIORITY = (
    'transaction_record',
    'authorization_result',
    'delivery_status',
    'refund_record',
    'cancellation_record',
    'merchant_description',
    'customer_history',
    'prior_disputes',
    'merchant_profile',
)


class Planner:
    def choose_tool(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        missing = set(state.get('missing_required_evidence', []))
        attempted = {entry.get('tool_name') for entry in state.get('tool_history', [])}
        for evidence_type in EVIDENCE_PRIORITY:
            if evidence_type not in missing:
                continue
            tool_name, argument_name = EVIDENCE_TOOL_MAP[evidence_type]
            if tool_name in attempted:
                continue
            identifier = context.get(argument_name)
            if not identifier:
                continue
            return {
                'action': 'call_tool',
                'tool_name': tool_name,
                'arguments': {argument_name: identifier},
                'evidence_type': evidence_type,
                'reason': f'{evidence_type} is required by the deterministic rule and can be checked with {tool_name}.',
            }
        return {
            'action': 'stop_investigation',
            'reason': 'No untried allowlisted tool can retrieve the remaining required evidence.',
        }

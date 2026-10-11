from __future__ import annotations

import json
from typing import Any

from app.guardrails.pii_masking import mask_pii_data


class DraftingAgent:
    def draft(self, case: Any, decision: Any, evidence: list[Any]) -> str:
        evidence_lines = '\n'.join(
            f"{index}. {item.evidence_type}: {json.dumps(mask_pii_data(item.value), ensure_ascii=True, default=str)} [{item.evidence_id}]"
            for index, item in enumerate(evidence, start=1)
        ) or 'No supporting evidence was collected.'
        rationale = getattr(decision, 'rationale', None)
        if rationale is None and isinstance(decision, dict):
            rationale = decision.get('rationale')
        rationale = rationale or 'The deterministic review found the required evidence complete.'
        return f"""Subject: Representment Response - Case {case.case_id}

Dispute reason:
{case.dispute_reason_code}

Transaction:
{case.transaction_id}
Merchant:
{case.merchant_id}
Amount:
{case.amount} {getattr(case, 'currency', None) or 'INR'}

Summary:
This response is based only on the evidence records collected for this case.

Supporting Evidence:
{evidence_lines}

Reason for Contest:
{rationale}

Requested Action:
Please review the representment response and maintain the merchant's position.
"""

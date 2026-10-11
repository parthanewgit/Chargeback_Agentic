from __future__ import annotations

import json
from math import ceil
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from app.schemas.case import DisputeCase
from app.schemas.evidence import EvidenceItem
from app.services.case_service import CaseService


def run():
    data_path = Path(__file__).resolve().parent.parent / 'data' / 'synthetic_cases.json'
    cases = json.loads(data_path.read_text())
    evidence_path = Path(__file__).resolve().parent.parent / 'data' / 'synthetic_evidence.json'
    evidence_by_transaction = json.loads(evidence_path.read_text())
    case_service = CaseService()
    results = []
    latencies = []
    citation_count = 0
    valid_citation_count = 0
    relevant_citation_count = 0
    expected_citation_type_count = 0
    covered_citation_type_count = 0
    total_tool_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    for entry in cases:
        case_evidence = [
            EvidenceItem(
                evidence_id=f'EVAL-{index:03d}',
                evidence_type=item['evidence_type'],
                source='synthetic_fixture',
                value=item['value'],
                reliability=0.9,
            )
            for index, item in enumerate(evidence_by_transaction.get(entry['transaction_id'], []), start=1)
        ]
        case = DisputeCase(
            case_id=entry['case_id'],
            dispute_reason_code=entry['dispute_reason_code'],
            transaction_id=entry['transaction_id'],
            amount=entry.get('amount'),
            currency=entry.get('currency'),
            merchant_id=entry.get('merchant_id'),
            customer_id=entry.get('customer_id'),
            response_deadline=entry.get('response_deadline'),
            merchant_evidence=case_evidence,
        )
        started = perf_counter()
        output = case_service.process_case(case, use_llm=False)
        latency_ms = (perf_counter() - started) * 1000
        latencies.append(latency_ms)
        evidence_by_id = {item['evidence_id']: item for item in output['collected_evidence']}
        citations = output['citations']
        valid_citations = [citation for citation in citations if citation in evidence_by_id]
        expected_citation_types = set(entry.get('required_citation_types', []))
        cited_types = {evidence_by_id[citation]['evidence_type'] for citation in valid_citations}
        relevant_citation_count += sum(
            1 for citation in valid_citations
            if evidence_by_id[citation]['evidence_type'] in expected_citation_types
        )
        citation_count += len(citations)
        valid_citation_count += len(valid_citations)
        expected_citation_type_count += len(expected_citation_types)
        covered_citation_type_count += len(cited_types & expected_citation_types)
        tool_calls = output['tool_history']
        total_tool_calls += len(tool_calls)
        total_prompt_tokens += output['token_usage'].get('prompt_tokens', 0)
        total_completion_tokens += output['token_usage'].get('completion_tokens', 0)
        results.append({
            'case_id': entry['case_id'],
            'expected_decision': entry['expected_decision'],
            'actual_decision': output['decision'],
            'expected_reason_code': entry.get('expected_reason_code'),
            'actual_reason_code': output['reason_code'],
            'expected_deadline_status': entry.get('expected_deadline_status'),
            'actual_deadline_status': output['deadline_status'],
            'expected_escalation': entry.get('expected_escalation'),
            'actual_escalation': output['requires_human_review'],
            'confidence': output['confidence'],
            'missing_evidence': output['missing_evidence'],
            'tool_calls': [call['tool_name'] for call in tool_calls],
            'citations': citations,
            'latency_ms': latency_ms,
        })
    total = len(cases)
    correct = sum(1 for row in results if row['expected_decision'] == row['actual_decision'])
    reason_correct = sum(1 for row in results if row['expected_reason_code'] == row['actual_reason_code'])
    deadline_checked = [row for row in results if row['expected_deadline_status'] is not None]
    deadline_correct = sum(1 for row in deadline_checked if row['expected_deadline_status'] == row['actual_deadline_status'])
    escalation_checked = [row for row in results if row['expected_escalation'] is not None]
    escalation_correct = sum(1 for row in escalation_checked if row['expected_escalation'] == row['actual_escalation'])
    true_positives = sum(1 for row in escalation_checked if row['expected_escalation'] and row['actual_escalation'])
    predicted_positives = sum(1 for row in escalation_checked if row['actual_escalation'])
    expected_positives = sum(1 for row in escalation_checked if row['expected_escalation'])
    sorted_latencies = sorted(latencies)
    p95_latency = sorted_latencies[max(0, ceil(0.95 * total) - 1)] if total else 0.0
    citation_validity = valid_citation_count / citation_count if citation_count else None
    citation_precision = relevant_citation_count / citation_count if citation_count else None
    citation_coverage = covered_citation_type_count / expected_citation_type_count if expected_citation_type_count else None
    error_analysis = [
        {
            **row,
            'likely_failure_reason': (
                'Decision mismatch; compare available evidence facts with the deterministic reason policy.'
                if row['expected_decision'] != row['actual_decision']
                else 'Deadline classification mismatch.'
                if row['expected_deadline_status'] != row['actual_deadline_status']
                else 'Escalation expectation mismatch.'
            ),
        }
        for row in results
        if (
            row['expected_decision'] != row['actual_decision']
            or row['expected_deadline_status'] != row['actual_deadline_status']
            or row['expected_escalation'] != row['actual_escalation']
        )
    ]
    summary = {
        'cases': total,
        'decision_accuracy': correct / total if total else 0.0,
        'correct_decisions': correct,
        'reason_code_accuracy': reason_correct / total if total else 0.0,
        'deadline_correctness': deadline_correct / len(deadline_checked) if deadline_checked else None,
        'escalation_accuracy': escalation_correct / len(escalation_checked) if escalation_checked else None,
        'escalation_precision': true_positives / predicted_positives if predicted_positives else None,
        'escalation_recall': true_positives / expected_positives if expected_positives else None,
        'citation_validity_rate': citation_validity,
        'citation_relevance_precision': citation_precision,
        'required_citation_type_coverage': citation_coverage,
        'mean_latency_ms': mean(latencies) if latencies else 0.0,
        'median_latency_ms': median(latencies) if latencies else 0.0,
        'p95_latency_ms': p95_latency,
        'min_latency_ms': min(latencies) if latencies else 0.0,
        'max_latency_ms': max(latencies) if latencies else 0.0,
        'tool_calls': total_tool_calls,
        'average_tool_calls_per_case': total_tool_calls / total if total else 0.0,
        'model_calls': 0,
        'prompt_tokens': total_prompt_tokens,
        'completion_tokens': total_completion_tokens,
        'total_tokens': total_prompt_tokens + total_completion_tokens,
        'estimated_local_model_cost_usd': 0.0,
        'llm_enabled': False,
    }
    print(f"Evaluation cases: {total}")
    print(f"Decision accuracy: {correct}/{total} ({summary['decision_accuracy']:.2%})")
    print(f"Deadline correctness: {summary['deadline_correctness']:.2%}" if summary['deadline_correctness'] is not None else 'Deadline correctness: N/A')
    print(f"Citation validity: {summary['citation_validity_rate']:.2%}" if summary['citation_validity_rate'] is not None else 'Citation validity: N/A')
    print(f"Escalation accuracy: {summary['escalation_accuracy']:.2%}" if summary['escalation_accuracy'] is not None else 'Escalation accuracy: N/A')
    print(f"Mean latency: {summary['mean_latency_ms']:.2f} ms; p95: {summary['p95_latency_ms']:.2f} ms")
    print(f"Tool calls: {total_tool_calls}; LLM calls: 0 (deterministic benchmark)")
    out_path = Path(__file__).resolve().parent / 'results.json'
    report = {'summary': summary, 'results': results, 'error_analysis': error_analysis}
    out_path.write_text(json.dumps(report, indent=2))
    error_path = Path(__file__).resolve().parent / 'error_analysis.json'
    error_path.write_text(json.dumps(error_analysis, indent=2))
    return report


if __name__ == '__main__':
    run()

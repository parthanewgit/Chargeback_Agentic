from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from langgraph.graph import END, START, StateGraph
from opentelemetry import trace

from app.config import settings
from app.agents.decision_agent import DecisionAgent
from app.agents.drafting_agent import DraftingAgent
from app.agents.investigator import Investigator
from app.agents.planner import Planner
from app.agents.state import DisputeAgentState
from app.guardrails.grounding import validate_citations
from app.guardrails.injection_detection import detect_prompt_injection
from app.guardrails.pii_masking import mask_pii, mask_pii_data
from app.llm.ollama_provider import OllamaProviderError, OllamaResponseError
from app.llm.prompts import CASE_REVIEW_PROMPT, CORE_SYSTEM_PROMPT
from app.llm.provider_factory import create_llm_provider
from app.llm.structured_output import DecisionExplanation
from app.observability.metrics import metrics
from app.observability.tracing import trace_span
from app.rules.deadlines import evaluate_deadline
from app.rules.reason_codes import normalize_reason_code
from app.rules.rule_engine import get_rule_for_reason
from app.schemas.decision import DecisionOutput
from app.schemas.evidence import EvidenceItem
from app.services.audit_service import AuditService

TOOL_EVIDENCE_FIELDS = {
    'get_transaction': {
        'transaction_record': ('transaction_id', 'amount', 'currency', 'timestamp', 'merchant_id', 'country', 'country_code', 'payment_network', 'merchant_city', 'merchant_state'),
        'authorization_result': ('authorization_status', 'three_ds', 'avs_result', 'cvv_result', 'device_id', 'ip_country'),
        'refund_record': ('refund_status', 'refund_transaction_id', 'refund_timestamp', 'refund_amount'),
    },
    'get_delivery_status': {
        'delivery_status': ('delivery_status', 'tracking_number', 'delivery_timestamp', 'carrier', 'address_match', 'signature_required', 'delivery_city', 'delivery_state', 'postal_code', 'country'),
    },
    'get_customer_history': {
        'customer_history': ('past_disputes', 'chargeback_history', 'order_count', 'customer_tenure_days', 'country', 'city', 'state', 'postal_code', 'locale'),
        'cancellation_record': ('cancellation_status', 'cancellation_timestamp'),
    },
    'get_prior_disputes': {
        'prior_disputes': ('dispute_count', 'prior_outcomes', 'recent_pattern'),
    },
    'get_merchant_profile': {
        'merchant_profile': ('merchant_name', 'merchant_tier', 'returns_policy', 'shipping_window_days', 'country', 'city', 'state', 'postal_code', 'currency', 'support_phone'),
        'merchant_description': ('description_matches',),
    },
}

DECISION_SUPPORT_TYPES = {
    'fraud_card_not_present': {'transaction_record', 'authorization_result'},
    'item_not_received': {'transaction_record', 'delivery_status'},
    'duplicate_processing': {'transaction_record', 'prior_disputes'},
    'credit_not_processed': {'transaction_record', 'refund_record'},
    'not_as_described': {'transaction_record', 'merchant_description'},
    'cancelled_recurring': {'transaction_record', 'cancellation_record'},
}


class ChargebackGraph:
    def __init__(self, llm_provider: Any | None = None):
        self.planner = Planner()
        self.investigator = Investigator()
        self.decision_agent = DecisionAgent()
        self.drafting_agent = DraftingAgent()
        self.llm_provider = llm_provider or create_llm_provider()
        self.investigation_graph = self._build_investigation_graph()

    def _build_investigation_graph(self):
        builder = StateGraph(DisputeAgentState)
        builder.add_node('planner_node', self._plan_investigation)
        builder.add_node('tool_node', self._execute_investigation_tool)
        builder.add_edge(START, 'planner_node')
        builder.add_conditional_edges(
            'planner_node',
            self._route_investigation,
            {'execute_tool': 'tool_node', 'stop': END},
        )
        builder.add_edge('tool_node', 'planner_node')
        return builder.compile()

    def _plan_investigation(self, state: DisputeAgentState) -> dict[str, Any]:
        iteration = state.get('investigation_iteration', 0) + 1
        steps = list(state.get('investigation_steps', []))
        if iteration > settings.MAX_AGENT_ITERATIONS:
            plan = {'action': 'stop_investigation', 'reason': 'Maximum planner iterations reached.'}
            steps.append({'step': 'iteration_limit_reached'})
        else:
            plan = self.planner.choose_tool(
                state,
                state.get('planner_context', {}),
            )
            if plan['action'] != 'call_tool':
                steps.append({'step': 'stop_investigation', 'reason': plan['reason']})
        return {'plan': plan, 'investigation_iteration': iteration, 'investigation_steps': steps}

    @staticmethod
    def _route_investigation(state: DisputeAgentState) -> str:
        plan = state.get('plan', {})
        if plan.get('action') != 'call_tool':
            return 'stop'
        if len(state.get('tool_history', [])) >= settings.MAX_TOOL_CALLS:
            return 'stop'
        return 'execute_tool'

    def _execute_investigation_tool(self, state: DisputeAgentState) -> dict[str, Any]:
        plan = state['plan']
        history = list(state.get('tool_history', []))
        evidence = list(state.get('evidence', []))
        steps = list(state.get('investigation_steps', []))
        audit_events = list(state.get('audit_events', []))
        tool_result: dict[str, Any] = {'error': 'tool_call_not_attempted'}
        attempts = 0
        for attempt in range(settings.MAX_SAME_TOOL_RETRIES + 1):
            if len(history) >= settings.MAX_TOOL_CALLS:
                break
            attempts = attempt + 1
            try:
                metrics.increment('tool_calls')
                with trace_span('investigation_tool_call', tool_name=plan['tool_name']):
                    tool_result = self.investigator.run(plan)
            except Exception as exc:
                tool_result = {'error': str(exc)}
            history.append({**plan, 'attempt': attempts, 'result': tool_result})
            if 'error' not in tool_result:
                break

        tool_status = 'failed' if 'error' in tool_result else 'completed'
        steps.append({
            'step': 'tool_completed',
            'tool_name': plan['tool_name'],
            'reason': plan['reason'],
            'status': tool_status,
            'attempts': attempts,
        })
        audit_events.append({
            'step': 'tool_completed',
            'case_id': state['case'].case_id,
            'tool_name': plan['tool_name'],
            'status': tool_status,
            'attempts': attempts,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        existing_types = {item.evidence_type for item in evidence}
        for evidence_type, fields in TOOL_EVIDENCE_FIELDS.get(plan['tool_name'], {}).items():
            if evidence_type in existing_types:
                continue
            value = {field: tool_result[field] for field in fields if field in tool_result}
            if value and 'error' not in tool_result:
                evidence.append(EvidenceItem(
                    evidence_id=f'EVID-{len(evidence) + 1:03d}',
                    evidence_type=evidence_type,
                    source=plan['tool_name'],
                    value=value,
                    reliability=0.9,
                ))
                existing_types.add(evidence_type)
        present = {item.evidence_type for item in evidence}
        missing = sorted(set(state.get('missing_required_evidence', [])) - present)
        return {
            'evidence': evidence,
            'missing_required_evidence': missing,
            'tool_history': history,
            'investigation_steps': steps,
            'audit_events': audit_events,
        }

    def process_case(self, case: Any, use_llm: bool = True) -> dict[str, Any]:
        started = perf_counter()
        metrics.increment('cases_processed')
        with trace_span(
            'case_processing',
            case_id=getattr(case, 'case_id', None),
            reason_code=str(getattr(case, 'dispute_reason_code', 'unknown')),
        ):
            result = self._process_case(case, use_llm)
        latency_ms = (perf_counter() - started) * 1000
        result['latency'] = latency_ms
        metrics.increment(f"decision_{result['decision'].value if hasattr(result['decision'], 'value') else result['decision']}")
        metrics.increment('case_latency_ms', latency_ms)
        return result

    def _process_case(self, case: Any, use_llm: bool = True) -> dict[str, Any]:
        reason_code = normalize_reason_code(getattr(case, 'dispute_reason_code', None) or 'unknown') or 'unknown'
        evidence = list(getattr(case, 'merchant_evidence', []))
        deadline = evaluate_deadline(getattr(case, 'response_deadline', None), datetime.now(timezone.utc))
        tool_history: list[dict[str, Any]] = []
        investigation_steps: list[dict[str, Any]] = []
        audit_events = [{'step': 'case_received', 'case_id': case.case_id, 'timestamp': datetime.now(timezone.utc).isoformat()}]
        try:
            required_evidence = get_rule_for_reason(reason_code).required_evidence
        except ValueError:
            required_evidence = []
        if not deadline.expired:
            present_types = {item.evidence_type for item in evidence}
            investigation_state = self.investigation_graph.invoke({
                'case': case,
                'reason_code': reason_code,
                'evidence': evidence,
                'missing_required_evidence': sorted(set(required_evidence) - present_types),
                'tool_history': [],
                'investigation_steps': [],
                'audit_events': audit_events,
                'planner_context': {
                    'transaction_id': getattr(case, 'transaction_id', None),
                    'customer_id': getattr(case, 'customer_id', None),
                    'merchant_id': getattr(case, 'merchant_id', None),
                },
                'investigation_iteration': 0,
            })
            evidence = investigation_state.get('evidence', evidence)
            tool_history = investigation_state.get('tool_history', [])
            investigation_steps = investigation_state.get('investigation_steps', [])
            audit_events = investigation_state.get('audit_events', audit_events)
        decision = self.decision_agent.decide(case, evidence, [], deadline.status.value, reason_code)
        rationale = 'Deterministic review completed using available evidence and rule checks.'
        citations: list[str] = []
        llm_status = 'not_used'
        llm_error: str | None = None
        model_usage = 'deterministic-rules'
        security_flags: list[str] = []
        if any(detect_prompt_injection(text) for text in [
            getattr(case, 'dispute_description', None),
            *(getattr(document, 'content', None) for document in getattr(case, 'source_documents', [])),
            *(json.dumps(item.value, ensure_ascii=True, default=str) for item in evidence),
        ]):
            security_flags.append('prompt_injection_detected')
            audit_events.append({
                'step': 'prompt_injection_detected',
                'case_id': case.case_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

        if use_llm:
            case_data = {
                'case_id': case.case_id,
                'reason_code': reason_code,
                'transaction_id': getattr(case, 'transaction_id', None),
                'amount': str(getattr(case, 'amount', None)) if getattr(case, 'amount', None) is not None else None,
                'description': getattr(case, 'dispute_description', None),
                'decision': decision['decision'],
                'missing_evidence': decision['missing_evidence'],
                'missing_fields': getattr(case, 'missing_fields', []),
                'conflicting_fields': [item.model_dump(mode='json') for item in getattr(case, 'conflicting_fields', [])],
                'valid_evidence_ids': [item.evidence_id for item in evidence],
                'evidence': [item.model_dump(mode='json') for item in evidence],
                'documents': [
                    {
                        'name': document.name,
                        'kind': document.kind,
                        'content': (document.content or '')[:12000],
                    }
                    for document in getattr(case, 'source_documents', [])
                ],
            }
            safe_case_json = json.dumps(mask_pii_data(case_data), ensure_ascii=True, default=str)
            prompt = f'{CORE_SYSTEM_PROMPT}\n\n{CASE_REVIEW_PROMPT.format(case_json=safe_case_json)}'
            model_usage = f'ollama/{self.llm_provider.model}'
            try:
                with trace_span('llm_explanation', model=model_usage):
                    metrics.increment('llm_calls')
                    model_result = asyncio.run(
                        self.llm_provider.structured_generate(
                            prompt,
                            schema=DecisionExplanation,
                            think=False,
                            options={'num_predict': 96, 'num_ctx': 2048, 'temperature': 0.1},
                            keep_alive='10m',
                        )
                    )
                metrics.increment('llm_prompt_tokens', getattr(self.llm_provider, 'last_usage', {}).get('prompt_tokens', 0))
                metrics.increment('llm_completion_tokens', getattr(self.llm_provider, 'last_usage', {}).get('completion_tokens', 0))
                if isinstance(model_result, DecisionExplanation):
                    model_rationale = model_result.rationale
                    model_citations = model_result.citations
                else:
                    model_rationale = model_result.get('rationale')
                    model_citations = model_result.get('citations', [])
                if not isinstance(model_rationale, str) or not model_rationale.strip():
                    raise ValueError('Ollama response did not include a rationale.')
                if not isinstance(model_citations, list) or not all(isinstance(item, str) for item in model_citations):
                    raise ValueError('Ollama response included malformed citations.')
                valid, invalid = validate_citations(model_citations, {item.evidence_id for item in evidence})
                if not valid:
                    raise ValueError(f'Ollama returned unknown evidence IDs: {", ".join(invalid)}')
                rationale = model_rationale.strip()
                citations = model_citations
                llm_status = 'used'
                model_usage = f'ollama/{self.llm_provider.model}'
            except OllamaResponseError as exc:
                llm_status = 'invalid_output'
                llm_error = mask_pii(str(exc))
            except OllamaProviderError as exc:
                llm_status = 'unavailable'
                llm_error = mask_pii(str(exc))
            except Exception as exc:
                llm_status = 'invalid_output'
                llm_error = mask_pii(str(exc))
            audit_events.append({
                'step': 'llm_explanation_generated',
                'case_id': case.case_id,
                'status': llm_status,
                'model': model_usage,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

        if llm_status != 'used':
            reason_key = getattr(reason_code, 'value', str(reason_code))
            support_types = DECISION_SUPPORT_TYPES.get(reason_key, set())
            citations = [
                item.evidence_id
                for item in evidence
                if item.evidence_type in support_types
            ]
            if decision['missing_evidence']:
                rationale = (
                    f"The deterministic review recommends {decision['decision']} because required evidence is missing: "
                    f"{', '.join(decision['missing_evidence'])}."
                )
            else:
                rationale = f"The deterministic review recommends {decision['decision']} under the {reason_code} evidence rules."
            if citations:
                rationale += ' Collected evidence: ' + ', '.join(f'[{citation}]' for citation in citations) + '.'

        valid, invalid = validate_citations(citations, {ev.evidence_id for ev in evidence})
        review_reasons = []
        if decision['confidence'] < settings.HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
            review_reasons.append('confidence below configured threshold')
        if getattr(case, 'amount', None) is not None and float(case.amount) > settings.HIGH_VALUE_CASE_THRESHOLD:
            review_reasons.append('amount exceeds configured high-value threshold')
        if getattr(case, 'conflicting_fields', []):
            review_reasons.append('conflicting case fields')
        if getattr(case, 'missing_fields', []):
            review_reasons.append('required intake fields are missing')
        if deadline.status.value == 'UNKNOWN':
            review_reasons.append('response deadline is unknown')
        if security_flags:
            review_reasons.append('prompt injection detected in untrusted evidence')
        if llm_status == 'invalid_output':
            review_reasons.append('LLM output failed validation')
        if not valid:
            review_reasons.append('invalid evidence citations')
        if reason_code == 'unknown':
            review_reasons.append('unsupported or missing reason code')
        safe_tool_history = mask_pii_data(tool_history)
        if review_reasons:
            audit_events.append({
                'step': 'human_review_required',
                'case_id': case.case_id,
                'reasons': review_reasons,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
        output = DecisionOutput(
            case_id=case.case_id,
            reason_code=reason_code,
            decision=decision['decision'],
            confidence=float(decision['confidence']),
            deadline_status=deadline.status.value,
            evidence_complete=decision['evidence_complete'],
            rationale=rationale,
            citations=citations,
            missing_evidence=decision['missing_evidence'],
            required_evidence=required_evidence,
            collected_evidence=[item.model_dump(mode='json') for item in evidence],
            requires_human_review=bool(review_reasons),
            escalation_reason='; '.join(review_reasons) or None,
            latency=float(getattr(self.llm_provider, 'last_latency', 0.0)) if use_llm else 0.0,
            model_usage=model_usage,
            llm_status=llm_status,
            llm_error=llm_error,
            token_usage=getattr(self.llm_provider, 'last_usage', {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}) if use_llm else {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            investigation_steps=investigation_steps,
            tool_history=safe_tool_history,
            audit_events=audit_events,
            security_flags=security_flags,
            created_at=datetime.now(timezone.utc),
        )
        if output.decision == 'CONTEST':
            output.representment_letter = self.drafting_agent.draft(case, output, evidence)
        audit_events.append({
            'step': 'decision_generated',
            'case_id': case.case_id,
            'decision': output.decision,
            'confidence': output.confidence,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        span_context = trace.get_current_span().get_span_context()
        trace_id = f'{span_context.trace_id:032x}' if span_context.is_valid else case.case_id
        for event in audit_events:
            event['trace_id'] = trace_id
        AuditService().log_many(audit_events)
        return output.model_dump()

from __future__ import annotations

import sys
from datetime import datetime, time, timezone
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.case import DisputeCase
from app.schemas.feedback import FeedbackSubmission
from app.schemas.evidence import EvidenceItem
from app.services.document_extractor import extract_uploaded_document
from app.intake.extractor import extract_case_from_inputs, merge_manual_case_fields
from app.rules.reason_codes import ReasonCode
from app.rules.rule_engine import DEFAULT_RULES, get_rule_for_reason
from app.guardrails.pii_masking import mask_pii_data
from app.services.case_service import CaseService
from app.services.feedback_service import FeedbackService


def build_masked_case_preview(case) -> dict:
    payload = {
        'case_id': getattr(case, 'case_id', None),
        'transaction_id': getattr(case, 'transaction_id', None),
        'reason_code': getattr(case, 'dispute_reason_code', None),
        'amount': getattr(case, 'amount', None),
        'currency': getattr(case, 'currency', None),
        'dispute_description': getattr(case, 'dispute_description', None),
        'merchant_evidence': [
            evidence.model_dump(mode='json') if hasattr(evidence, 'model_dump') else evidence
            for evidence in getattr(case, 'merchant_evidence', [])
        ],
    }
    return mask_pii_data(payload)

st.set_page_config(page_title='Chargeback Analyst', page_icon='💳')
st.title('Chargeback Dispute Resolution Assistant')
st.caption('Created By Parthasarathi Mishra')

with st.container():
    case_id = st.text_input('Case ID', placeholder='Enter or extract from a document')
    transaction_id = st.text_input('Transaction ID', placeholder='Enter or extract from a document')
    reason_code = st.selectbox(
        'Dispute reason',
        options=[None, *ReasonCode],
        format_func=lambda code: 'Auto-detect from documents' if code is None else code.value.replace('_', ' ').title(),
    )
    amount = st.number_input('Disputed amount (INR)', min_value=0.0, value=0.0, step=1.0)
    dispute_description = st.text_area(
        'Case details or pasted email text',
        height=120,
        help='Paste the dispute email or summarize the case. Labeled IDs, amounts, reasons, and dates are extracted when present.',
    )
    has_response_deadline = st.checkbox('Enter response deadline')
    response_deadline_date = st.date_input('Response deadline', disabled=not has_response_deadline)
    uploaded_files = st.file_uploader(
        'Upload evidence files',
        type=['pdf', 'png', 'jpg', 'jpeg', 'eml', 'txt'],
        accept_multiple_files=True,
        help='PDF and email text are extracted. Images are previewed but not OCR-read; describe image details in Case details.',
    )
    if reason_code is None:
        evidence_options = sorted({evidence for rule in DEFAULT_RULES.values() for evidence in rule.required_evidence + rule.optional_evidence})
    else:
        reason_rule = get_rule_for_reason(reason_code.value)
        evidence_options = sorted(set(reason_rule.required_evidence + reason_rule.optional_evidence))
    selected_evidence = st.multiselect(
        'Evidence available',
        options=evidence_options,
        help='Select evidence types actually present in the case. Uploading a file does not automatically classify or verify its evidence.',
    )
    submitted = st.button('Submit Case')

for uploaded_file in uploaded_files:
    if uploaded_file.type.startswith('image/'):
        st.image(uploaded_file.getvalue(), caption=uploaded_file.name, width=400)

if submitted:
    try:
        source_documents = [
            extract_uploaded_document(uploaded_file.name, uploaded_file.getvalue())
            for uploaded_file in uploaded_files
        ]
        pdf_text = '\n'.join(document.content or '' for document in source_documents if document.kind == 'pdf')
        email_text = '\n'.join(filter(None, [
            *(document.content or '' for document in source_documents if document.kind in {'email', 'email_text'}),
            dispute_description.strip(),
        ]))
        image_documents = [document for document in source_documents if document.kind == 'image']
        extracted_case = extract_case_from_inputs(
            case_id.strip() or None,
            pdf_text=pdf_text or None,
            email_text=email_text or None,
            image_summary=(
                {'filename': image_documents[0].name, 'text': image_documents[0].content}
                if image_documents else None
            ),
        )
        extracted_case.source_documents = source_documents
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    evidence = [
        EvidenceItem(
            evidence_id=f'EVID-{index:03d}',
            evidence_type=evidence_type,
            source='analyst_input',
            value='Provided',
        )
        for index, evidence_type in enumerate(selected_evidence, start=1)
    ]
    case = merge_manual_case_fields(
        extracted_case,
        case_id=case_id.strip() or None,
        transaction_id=transaction_id.strip() or None,
        reason_code=reason_code.value if reason_code else None,
        amount=amount or None,
        currency='INR' if amount else None,
        response_deadline=datetime.combine(response_deadline_date, time.max, tzinfo=timezone.utc) if has_response_deadline else None,
        merchant_evidence=evidence,
    )
    st.session_state['masked_case_preview'] = build_masked_case_preview(case)
    st.session_state['case_result'] = CaseService().process_case(case)
    st.session_state.pop('analyst_disposition', None)

result = st.session_state.get('case_result')
if result:
    st.subheader(f"Review: {result['case_id']}")
    decision = result['decision']
    if decision == 'CONTEST':
        st.success(f'Recommendation: {decision.replace("_", " ").title()}')
    elif decision == 'ACCEPT':
        st.warning(f'Recommendation: {decision.replace("_", " ").title()}')
    else:
        st.info(f'Recommendation: {decision.replace("_", " ").title()}')

    first, second, third = st.columns(3)
    first.metric('Confidence', f"{result['confidence']:.0%}")
    second.metric('Evidence', 'Complete' if result['evidence_complete'] else 'Incomplete')
    third.metric('Deadline', result['deadline_status'].replace('_', ' ').title())

    st.markdown('**Reasoning**')
    st.write(result['rationale'])
    if result.get('llm_status') == 'used':
        st.caption(f"Explanation generated by {result['model_usage']}")
    elif result.get('llm_status') == 'unavailable':
        st.caption('Using deterministic fallback reasoning because Ollama was unavailable.')
        if result.get('llm_error'):
            st.caption(f"Ollama detail: {result['llm_error']}")
    elif result.get('llm_status') == 'invalid_output':
        st.caption('Using deterministic fallback reasoning because the Ollama response was rejected.')
        if result.get('llm_error'):
            st.caption(f"Validation detail: {result['llm_error']}")
    if result['missing_evidence']:
        st.markdown('**Missing evidence**')
        st.write(', '.join(result['missing_evidence']))
    st.markdown('**Evidence review**')
    st.write(f"Required: {', '.join(result['required_evidence']) or 'None'}")
    st.write(f"Collected: {', '.join(item['evidence_type'] for item in result['collected_evidence']) or 'None'}")
    if result.get('escalation_reason'):
        st.warning(f"Human review required: {result['escalation_reason']}")

    masked_preview = st.session_state.get('masked_case_preview')
    if masked_preview:
        st.markdown('**Masked case preview**')
        st.json(masked_preview, expanded=False)

    if result.get('investigation_steps'):
        with st.expander('Investigation Steps'):
            for index, step in enumerate(result['investigation_steps'], start=1):
                st.write(f"{index}. {step.get('tool_name', step.get('step', 'review')).replace('_', ' ').title()}: {step.get('reason', step.get('status', 'completed'))}")

    st.markdown('**Analyst decision**')
    approve_col, reject_col, edit_col = st.columns(3)
    if approve_col.button('Approve recommendation', use_container_width=True):
        try:
            saved = FeedbackService().record(FeedbackSubmission(
                case_id=result['case_id'],
                original_decision=result['decision'],
                analyst_action='APPROVE',
                final_decision=result['decision'],
            ))
            st.session_state['analyst_disposition'] = saved['analyst_action']
            st.session_state.pop('pending_analyst_action', None)
        except Exception as exc:
            st.error(f'Could not save analyst decision: {exc}')
    if reject_col.button('Reject recommendation', use_container_width=True):
        st.session_state['pending_analyst_action'] = 'REJECT'
    if edit_col.button('Edit decision', use_container_width=True):
        st.session_state['pending_analyst_action'] = 'EDIT'

    pending_action = st.session_state.get('pending_analyst_action')
    if pending_action:
        allowed_decisions = ['ACCEPT', 'CONTEST', 'REQUEST_MORE_INFO']
        if pending_action == 'REJECT':
            allowed_decisions = [value for value in allowed_decisions if value != result['decision']]
        with st.form('analyst_feedback_form'):
            final_decision = st.selectbox(
                'Final decision',
                options=allowed_decisions,
                index=allowed_decisions.index(result['decision']) if result['decision'] in allowed_decisions else 0,
            )
            analyst_comment = st.text_area('Analyst comment')
            save_feedback = st.form_submit_button('Save analyst decision')
        if save_feedback:
            try:
                saved = FeedbackService().record(FeedbackSubmission(
                    case_id=result['case_id'],
                    original_decision=result['decision'],
                    analyst_action=pending_action,
                    final_decision=final_decision,
                    comment=analyst_comment.strip() or None,
                ))
                st.session_state['analyst_disposition'] = saved['analyst_action']
                st.session_state['analyst_final_decision'] = saved['final_decision']
                st.session_state.pop('pending_analyst_action', None)
            except Exception as exc:
                st.error(f'Could not save analyst decision: {exc}')
    if disposition := st.session_state.get('analyst_disposition'):
        final_decision = st.session_state.get('analyst_final_decision', result['decision'])
        st.success(f"Saved {disposition.lower()} action. Final decision: {final_decision}.")

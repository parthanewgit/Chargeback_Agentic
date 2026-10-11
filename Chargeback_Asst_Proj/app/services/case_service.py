from __future__ import annotations

import json

from app.persistence.database import SessionLocal, create_schema
from app.persistence.models import CaseRecord
from app.guardrails.pii_masking import mask_pii_data
from app.rules.reason_codes import normalize_reason_code
from app.services.decision_service import DecisionService


class CaseService:
    def __init__(self, decision_service=None, session_factory=SessionLocal, schema_creator=create_schema):
        self.decision_service = decision_service or DecisionService()
        self.session_factory = session_factory
        self.schema_creator = schema_creator

    def process_case(self, case, use_llm: bool = True):
        if case.dispute_reason_code:
            case.dispute_reason_code = normalize_reason_code(str(case.dispute_reason_code)) or case.dispute_reason_code
        result = self.decision_service.process(case, use_llm=use_llm)
        self.store_case(case, result=result, status='processed')
        return result

    def store_case(self, case, result=None, status: str = 'received'):
        self.schema_creator()
        case_id = case.case_id
        case_data = json.dumps(mask_pii_data(case.model_dump(mode='json')), ensure_ascii=True, default=str)
        payload = json.dumps(mask_pii_data(result), ensure_ascii=True, default=str) if result is not None else None
        with self.session_factory() as session:
            record = session.get(CaseRecord, case_id)
            if record is None:
                record = CaseRecord(id=case_id)
                session.add(record)
            record.reason_code = str(case.dispute_reason_code or '')
            record.status = status
            record.case_data = case_data
            record.payload = payload
            if result is not None:
                record.decision = str(result.get('decision', ''))
                record.confidence = float(result.get('confidence', 0.0))
            session.commit()
            return self._record_dict(record)

    def get_case(self, case_id: str):
        self.schema_creator()
        with self.session_factory() as session:
            record = session.get(CaseRecord, case_id)
            return self._record_dict(record) if record is not None else None

    @staticmethod
    def _record_dict(record):
        return {
            'case_id': record.id,
            'reason_code': record.reason_code,
            'decision': record.decision,
            'confidence': record.confidence,
            'status': record.status,
            'case_data': json.loads(record.case_data) if record.case_data else None,
            'result': json.loads(record.payload) if record.payload else None,
        }

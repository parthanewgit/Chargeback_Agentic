from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.database import SessionLocal, create_schema
from app.guardrails.pii_masking import mask_pii
from app.services.audit_service import AuditService


class FeedbackService:
    def __init__(self, session_factory=SessionLocal, schema_creator=create_schema, audit_service=None):
        self.session_factory = session_factory
        self.schema_creator = schema_creator
        self.audit_service = audit_service or AuditService()

    def record(self, item: Any) -> dict[str, Any]:
        from app.persistence.models import FeedbackRecord

        self.schema_creator()
        data = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
        data['timestamp'] = data.get('timestamp') or datetime.now(timezone.utc)
        if data.get('comment'):
            data['comment'] = mask_pii(data['comment'])
        with self.session_factory() as session:
            record = FeedbackRecord(**data)
            session.add(record)
            session.commit()
            session.refresh(record)
            stored = {
                'id': record.id,
                'case_id': record.case_id,
                'original_decision': record.original_decision,
                'analyst_action': record.analyst_action,
                'final_decision': record.final_decision,
                'comment': record.comment,
                'timestamp': record.timestamp.isoformat(),
            }
        self.audit_service.log_many([{
            'step': 'analyst_action',
            'case_id': stored['case_id'],
            'analyst_action': stored['analyst_action'],
            'final_decision': stored['final_decision'],
            'timestamp': stored['timestamp'],
        }])
        return stored

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.persistence.database import SessionLocal, create_schema
from app.persistence.models import AuditRecord


class AuditService:
    def __init__(self, session_factory=SessionLocal, schema_creator=create_schema):
        self.session_factory = session_factory
        self.schema_creator = schema_creator

    def log_many(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        self.schema_creator()
        with self.session_factory() as session:
            for event in events:
                event_timestamp = event.get('timestamp')
                if isinstance(event_timestamp, str):
                    event_timestamp = datetime.fromisoformat(event_timestamp)
                session.add(AuditRecord(
                    case_id=event.get('case_id', ''),
                    step=event.get('step', 'unknown'),
                    status=event.get('status', 'completed'),
                    trace_id=event.get('trace_id') or event.get('case_id'),
                    timestamp=event_timestamp,
                    details=json.dumps(event, ensure_ascii=True, default=str),
                ))
            session.commit()

    def list_for_case(self, case_id: str) -> list[dict[str, Any]]:
        self.schema_creator()
        with self.session_factory() as session:
            rows = session.query(AuditRecord).filter_by(case_id=case_id).order_by(AuditRecord.id).all()
            return [json.loads(row.details) for row in rows if row.details]

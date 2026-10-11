from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.case import DisputeCase
from app.services.audit_service import AuditService
from app.services.case_service import CaseService

router = APIRouter()
case_service = CaseService()


@router.post('/cases')
def create_case(case: DisputeCase):
    return case_service.store_case(case, status='accepted')


@router.post('/cases/{case_id}/process')
def process_case(case_id: str, case: DisputeCase):
    if case.case_id and case.case_id != case_id:
        raise HTTPException(status_code=400, detail='Case ID mismatch')
    return case_service.process_case(case)


@router.get('/cases/{case_id}')
def get_case(case_id: str):
    record = case_service.get_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Case not found')
    return record


@router.get('/cases/{case_id}/audit')
def get_audit(case_id: str):
    return {'case_id': case_id, 'events': AuditService().list_for_case(case_id)}

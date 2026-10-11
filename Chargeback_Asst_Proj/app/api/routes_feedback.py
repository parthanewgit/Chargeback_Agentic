from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.feedback import FeedbackSubmission
from app.services.feedback_service import FeedbackService

router = APIRouter()


@router.post('/cases/{case_id}/feedback')
def save_feedback(case_id: str, item: FeedbackSubmission):
    if item.case_id != case_id:
        raise HTTPException(status_code=400, detail='Case ID mismatch')
    stored = FeedbackService().record(item)
    return {'case_id': case_id, 'status': 'stored', 'feedback': stored}

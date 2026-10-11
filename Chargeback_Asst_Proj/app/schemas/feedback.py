from __future__ import annotations

from datetime import datetime

from typing import Literal

from pydantic import BaseModel


class FeedbackSubmission(BaseModel):
    case_id: str
    original_decision: str
    analyst_action: Literal['APPROVE', 'REJECT', 'EDIT']
    final_decision: Literal['ACCEPT', 'CONTEST', 'REQUEST_MORE_INFO']
    comment: str | None = None
    timestamp: datetime | None = None

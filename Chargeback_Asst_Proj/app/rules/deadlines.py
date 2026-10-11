from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class DeadlineStatus(str, Enum):
    VALID = 'VALID'
    EXPIRING_SOON = 'EXPIRING_SOON'
    EXPIRED = 'EXPIRED'
    UNKNOWN = 'UNKNOWN'


@dataclass
class DeadlineAssessment:
    status: DeadlineStatus
    remaining_days: float
    expired: bool
    contest_allowed: bool


def evaluate_deadline(deadline: datetime | None, now: datetime | None = None) -> DeadlineAssessment:
    if deadline is None:
        return DeadlineAssessment(DeadlineStatus.UNKNOWN, 0.0, False, False)
    if now is None:
        now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    remaining = deadline - now
    remaining_days = remaining.total_seconds() / 86400
    if remaining_days < 0:
        status = DeadlineStatus.EXPIRED
        contest_allowed = False
        expired = True
    elif remaining_days <= 1:
        status = DeadlineStatus.EXPIRING_SOON
        contest_allowed = True
        expired = False
    else:
        status = DeadlineStatus.VALID
        contest_allowed = True
        expired = False
    return DeadlineAssessment(status=status, remaining_days=remaining_days, expired=expired, contest_allowed=contest_allowed)

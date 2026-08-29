"""Decision memory helper — 1 entry point ghi decision_logs (plan 27 Task 1)."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.decision_log import DecisionLog
from app.models.enums import DecisionSubject


def log_decision(
    db: Session,
    *,
    product_id: uuid.UUID,
    subject_type: DecisionSubject,
    subject_id: uuid.UUID,
    agent_value: dict[str, Any] | None,
    human_value: dict[str, Any] | None,
    reason: str | None = None,
    reviewer_id: uuid.UUID | None = None,
) -> None:
    """Ghi 1 dòng decision log (commit do caller); KHÔNG bao giờ raise —
    memory thất bại không được phá flow nghiệp vụ chính."""
    try:
        db.add(
            DecisionLog(
                product_id=product_id,
                subject_type=subject_type,
                subject_id=subject_id,
                agent_value=agent_value,
                human_value=human_value,
                reason=reason,
                reviewer_id=reviewer_id,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 — memory là phụ, không chặn business
        db.rollback()

"""Insight review — Gate #2 HITL (VoC OS §43, plan 25).

Presence of row = human đã quyết insight; action approve|edit|
investigate_more|reject (enum insight_review_action, migration 0011).
investigate_more KHÔNG kết thúc insight — graph quay lại planner với feedback.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import INSIGHT_REVIEW_ACTION_ENUM, InsightReviewAction


class InsightReview(Base):
    __tablename__ = "insight_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    edited_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action: Mapped[InsightReviewAction] = mapped_column(
        INSIGHT_REVIEW_ACTION_ENUM, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

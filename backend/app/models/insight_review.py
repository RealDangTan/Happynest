"""Bảng insight_reviews — audit HITL INSIGHT-level (mirror human_reviews).

Khác biệt với human_reviews: gắn insight_id thay vì feedback_id; đây là
marker phân biệt auto-path vs HITL cho KPI phase 20 — insight auto-approved
KHÔNG có row ở bảng này (decisions 2026-08-26, owner duyệt).
Tái dùng review_action enum có sẵn — không tạo enum mới.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import REVIEW_ACTION_ENUM, ReviewAction


class InsightReview(Base):
    __tablename__ = "insight_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), nullable=False
    )
    original_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    edited_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action: Mapped[ReviewAction] = mapped_column(REVIEW_ACTION_ENUM, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

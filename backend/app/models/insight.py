"""Bảng insights — TẠO BÂY GIỜ, UNUSED phase này (insight generation là giai đoạn sau)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import REVIEW_STATUS_ENUM, ReviewStatus


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clusters.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # tái dùng đúng enum review_status của feedbacks
    review_status: Mapped[ReviewStatus] = mapped_column(
        REVIEW_STATUS_ENUM, nullable=False, default=ReviewStatus.unreviewed
    )

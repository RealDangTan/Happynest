"""Bảng insights — TẠO BÂY GIỜ, UNUSED phase này (insight generation là giai đoạn sau)."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
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
    # created_at bổ sung bởi migration 0007 (agent substrate): plan 20 tính
    # time_to_insight từ mốc này — bảng gốc 0003 không có.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Embedding precedent retrieval (phase 18 backfill điền); luôn lưu
    # model + dim kèm vector — mirror đúng feedbacks.embedding triplet ---
    embedding = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

"""Bảng feedbacks — trung tâm pipeline: ingest → sanitize → classify → embed."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    AI_ISSUE_ENUM,
    REVIEW_STATUS_ENUM,
    SENTIMENT_ENUM,
    SEVERITY_ENUM,
    AiIssue,
    ReviewStatus,
    Sentiment,
    Severity,
)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    # event time = thời điểm phản hồi diễn ra (do nguồn cung cấp), KHÔNG phải lúc insert
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- PII boundary: raw_content KHÔNG BAO GIỜ ra khỏi biên sanitize ---
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pii_entities: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # --- Kết quả classify (Phase 07 điền) ---
    # safety_issue là lệch §6 có chủ đích (decisions.md 2026-08-24): công thức
    # HITL cần truy vấn trực tiếp, không giấu trong categories/rationale.
    safety_issue: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    categories: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    ai_issue: Mapped[AiIssue | None] = mapped_column(AI_ISSUE_ENUM, nullable=True)
    sentiment: Mapped[Sentiment | None] = mapped_column(SENTIMENT_ENUM, nullable=True)
    severity: Mapped[Severity | None] = mapped_column(SEVERITY_ENUM, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- HITL trigger (compute now, graph later) ---
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        REVIEW_STATUS_ENUM, nullable=False, default=ReviewStatus.unreviewed
    )

    # --- Embedding (Phase 08 điền); luôn lưu model + dim kèm vector ---
    embedding = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )

    # --- Clustering (Phase 14 điền); noise HDBSCAN (-1) giữ NULL ---
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clusters.id"), nullable=True
    )

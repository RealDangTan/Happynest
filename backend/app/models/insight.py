"""Insight model (mới) — VoC OS §42/§57 (plan 25).

Finding (evidence-backed fact) vs Hypothesis (inference) TÁCH RIÊNG confidence
(§41) — không bao giờ trình bày hypothesis như root cause xác nhận. status:
pending → (Gate #2) approved | edited | rejected | investigating.
"""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    finding_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # {statement, confidence} — inference, KHÔNG phải fact xác nhận (§41)
    hypothesis: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    affected_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    impact: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # list evidence_id (string UUID) — insight không evidence là vi phạm §68
    evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    embedding = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

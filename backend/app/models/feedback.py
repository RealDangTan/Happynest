"""Bảng feedback — trung tâm VoC OS sau reshape 0008 (plan 21; VoC OS §15–17).

Bảng phẳng cũ (categories/ai_issue/sentiment/severity... từng cột) được thay
bởi 3 JSONB zones — KHÔNG BAO GIỜ trộn lẫn:
- `data`: chiều phân tích cấp product (app_version, plan, ...) — LISTEN ghi.
- `source_meta`: metadata riêng của nguồn (ticket_status, agent, ...).
- `ai_analysis`: diễn giải ngữ nghĩa pipeline ghi (topics, sentiment, severity,
  problem_type, analysis_version) — chỉ feedback_text và các zone này là dữ
  liệu phân tích; `raw_content` là PII boundary KHÔNG BAO GIỜ ra khỏi sanitize.

`occurred_at` = event time nguồn cung cấp (đổi tên từ `created_at` cũ);
`created_at` = mốc ghi row.
"""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imports.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # event time = thời điểm phản hồi diễn ra (do nguồn cung cấp), KHÔNG phải lúc insert
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- PII boundary: raw_content KHÔNG BAO GIỜ ra khỏi biên sanitize ---
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_detected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    pii_entities: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # --- JSONB zones (VoC OS §17) ---
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    source_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # pipeline ghi sau khi classify; marker "đã xử lý" = ai_analysis IS NOT NULL
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # --- Embedding; luôn lưu model + dim kèm vector ---
    embedding = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )

    # --- Clustering; noise HDBSCAN (-1) giữ NULL ---
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clusters.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Taxonomy model — canonical + emerging themes (VoC OS §20–21, plan 23).

Product Schema = chiều phân tích tồn tại (data JSONB); Taxonomy = khách hàng
đANG nói về gì (ai_analysis.topics). VoC OS §21: AI không tự mutate canonical —
topic mới không khớp → emerging theme (accumulate evidence) → human review.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Taxonomy(Base):
    __tablename__ = "taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomies.id"), nullable=True
    )
    # Canonical tiếng Anh (2026-10-23 — đảo quyết định 2026-10-22): nhãn codebook
    # nhất quán cho classify, không phụ thuộc ngôn ngữ feedback.
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Tên hiển thị tiếng Việt cho UI (FE hiển thị `name_vi ?? name`).
    name_vi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Plan 31: id ổn định cho topic label ("payment.payment_failure") — BẤT BIẾN
    # khi rename `name`. Unique (product_id, slug) WHERE NOT NULL (migration 0016).
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # canonical (human-governed) | emerging (AI đề xuất chờ duyệt)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="canonical")
    # active | pending_review | merged | rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # VoC OS §21: accumulate evidence trước khi human review
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

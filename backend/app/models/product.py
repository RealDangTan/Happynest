"""Bảng products — đơn vị scoping của VoC OS (quyết định 2026-08-28:
KHÔNG bảng workspaces — product = workspace, `products → feedback` trực tiếp).

Mọi bảng phân tích (feedback, imports, taxonomies, clusters, insights,
actions, decision_logs) sẽ trỏ product_id. Product switcher ở profile (FE sau).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Plan 31: bump mỗi lần human apply taxonomy (generate/recommend) — snapshot
    # vào feedback.ai_analysis.taxonomy_version để định danh dataset A/B.
    taxonomy_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

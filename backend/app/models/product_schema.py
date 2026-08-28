"""Bảng product_schemas — registry dimension phân tích của 1 product (VoC OS §8).

Dynamic + versioned + product-specific + human-governed: LLM mapper CHỈ propose,
Gate #1 (human) mới kích hoạt version mới. Physical PostgreSQL KHÔNG BAO GIỜ
thêm cột khi schema đổi — mọi product field sống trong `feedback.data` JSONB.

System core fields (feedback_text, occurred_at, source, source_record_id —
VoC OS §9) KHÔNG nằm trong definition: hằng số ở services/schema_registry.py.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductSchema(Base):
    __tablename__ = "product_schemas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # draft → active (Gate #1 approve) → superseded (version mới activate)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Bảng impact_checks — closed-loop "did the action work?" (plan 20).

cluster_id CHỈ LÀ SNAPSHOT UUID không FK: clusters bị DELETE-all mỗi lần
rerun clustering (phase 14) nên FK sẽ đứt; cluster_name giữ tên để đối
chiếu. insight_id FK SET NULL — xoá insight vẫn giữ phép đo lịch sử.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImpactCheck(Base):
    __tablename__ = "impact_checks"
    __table_args__ = (Index("ix_impact_checks_insight_id", "insight_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insights.id", ondelete="SET NULL"), nullable=True
    )
    # snapshot cụm tại lúc check — KHÔNG FK (lý do docstring)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    cluster_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    before_count: Mapped[int] = mapped_column(Integer, nullable=False)
    after_count: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Bảng clusters — TẠO BÂY GIỜ, UNUSED phase này (clustering là giai đoạn sau)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    previous_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    growth_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_emerging: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_spike: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # scale ưu tiên sẽ chốt ở giai đoạn clustering; để nullable từ đầu
    suggested_priority: Mapped[float | None] = mapped_column(Float, nullable=True)

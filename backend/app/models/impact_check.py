"""ImpactCheck model — closed-loop đo trước/sau action (plan 27 Task 2)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImpactCheck(Base):
    __tablename__ = "impact_checks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    before_count: Mapped[int] = mapped_column(Integer, nullable=False)
    after_count: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

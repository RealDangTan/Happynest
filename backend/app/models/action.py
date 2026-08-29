"""Action model — ACT layer (VoC OS §48, §51–52, §58; plan 26).

priority_score là DETERMINISTIC từ công thức §49 (weights configurable) — LLM
chỉ ESTIMATE impact/effort/urgency/confidence. Human override (Gate #3) ghi
vào human_* columns, vị trí agent giữ nguyên làm evaluation data (§52).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BUSINESS_FUNCTION_ENUM, BusinessFunction


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True
    )
    function: Mapped[BusinessFunction] = mapped_column(
        BUSINESS_FUNCTION_ENUM, nullable=False
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    effort: Mapped[int] = mapped_column(Integer, nullable=False)
    urgency: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    human_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    human_effort: Mapped[int | None] = mapped_column(Integer, nullable=True)
    human_urgency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # proposed | edited | accepted | rejected
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="proposed", server_default="proposed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Decision log — unified memory của 3 HITL gates (VoC OS §52–53; plan 27).

Dùng làm evaluation data + precedent retrieval; KHÔNG fine-tune sớm (§53).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DECISION_SUBJECT_ENUM, DecisionSubject


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    subject_type: Mapped[DecisionSubject] = mapped_column(
        DECISION_SUBJECT_ENUM, nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    # vị trí AI (proposal/estimate) — giữ nguyên để đo agreement/displacement
    agent_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # quyết định human cuối
    human_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

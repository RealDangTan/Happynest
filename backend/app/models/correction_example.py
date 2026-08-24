"""Bảng correction_examples — few-shot cho correction loop sau này. UNUSED phase này."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CorrectionExample(Base):
    __tablename__ = "correction_examples"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    feedback_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedbacks.id"), nullable=False
    )
    original_prediction: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    corrected_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

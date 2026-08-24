"""Bảng analysis_runs — một lượt chạy batch pipeline (Phase 09 sử dụng)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RUN_STATUS_ENUM, RunStatus


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[RunStatus] = mapped_column(
        RUN_STATUS_ENUM, nullable=False, default=RunStatus.running
    )
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

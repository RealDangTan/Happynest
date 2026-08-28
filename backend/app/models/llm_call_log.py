"""Bảng llm_call_logs — bằng chứng vĩnh viễn vendor-independent (song song Langfuse).

⚠️ PII boundary: bảng này chỉ chứa metadata call — KHÔNG BAO GIỜ lưu prompt/
response content thô (chỉ sanitized text được phép đi vào prompt từ Phase 07).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import LLM_CALL_TYPE_ENUM, LlmCallType


class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )
    # Truy vết call theo feedback — reference THUẦN (không FK): reshape 0008
    # drop bảng feedbacks cũ nên FK gỡ; log lịch sử sống sót với id cũ orphan.
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    call_type: Mapped[LlmCallType] = mapped_column(LLM_CALL_TYPE_ENUM, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

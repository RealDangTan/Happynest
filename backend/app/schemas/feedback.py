"""Pydantic schemas cho feedback — reshape VoC OS (plan 21).

Ranh giới PII: `raw_content` KHÔNG BAO GIỜ nằm trong response nào — kể cả
detail (toggle `?include_raw` cũ đã chết cùng feedback-level HITL; reviewer
cần text → `feedback_text` đã sanitize là dữ liệu phân tích hợp lệ).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackIn(BaseModel):
    """Body POST /api/feedbacks. `occurred_at` = EVENT TIME (thời điểm phản hồi
    diễn ra theo nguồn cung cấp); thiếu → service gán now() lúc ingest."""

    source: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    source_record_id: str | None = Field(default=None, max_length=255)
    occurred_at: datetime | None = None
    # Phân tích cấp product đi kèm khi nhập tay (LISTEN sau này điền từ mapping)
    data: dict[str, Any] = Field(default_factory=dict)
    source_meta: dict[str, Any] = Field(default_factory=dict)


class FeedbackOut(BaseModel):
    """Shape an toàn PII — KHÔNG chứa raw_content."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    import_id: UUID | None
    source: str
    source_record_id: str | None
    occurred_at: datetime
    imported_at: datetime
    feedback_text: str | None
    pii_detected: bool
    data: dict[str, Any]
    source_meta: dict[str, Any]
    ai_analysis: dict[str, Any] | None
    created_at: datetime


class FeedbackListOut(BaseModel):
    """Envelope phân trang cho GET /api/feedbacks."""

    items: list[FeedbackOut]
    total: int
    limit: int
    offset: int


class CsvImportError(BaseModel):
    row: int  # số dòng trong file CSV (header = dòng 1)
    reason: str


class CsvImportReport(BaseModel):
    imported: int
    failed: int
    errors: list[CsvImportError]
    import_id: UUID | None = None

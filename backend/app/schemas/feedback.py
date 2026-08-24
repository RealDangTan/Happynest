"""Pydantic schemas cho ingestion feedback — Phase 05 (05-feedback-ingestion.md §3.1).

Ranh giới PII: `raw_content` KHÔNG nằm trong `FeedbackOut` mặc định — chỉ lộ
qua `FeedbackDetailOut` khi query param `include_raw=true`. Mọi response khác
(list, POST, import) chỉ trả metadata + `sanitized_content` (còn NULL giai
đoạn này, Phase 06 điền).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewStatus, Severity


class FeedbackIn(BaseModel):
    """Body POST /api/feedbacks. `created_at` = EVENT TIME (thời điểm phản hồi
    diễn ra theo nguồn cung cấp); thiếu → service gán now() lúc ingest.
    Phân biệt với `imported_at` do DB server_default gán."""

    source: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    external_ref: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = None


class FeedbackOut(BaseModel):
    """Shape an toàn PII — KHÔNG chứa raw_content."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    external_ref: str | None
    created_at: datetime
    imported_at: datetime
    review_status: ReviewStatus
    severity: Severity | None
    categories: list[str] | None
    confidence: float | None
    requires_human_review: bool
    sanitized_content: str | None


class FeedbackDetailOut(FeedbackOut):
    """FeedbackOut + raw_content — CHỈ dùng cho GET detail `?include_raw=true`."""

    raw_content: str


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

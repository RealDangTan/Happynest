"""Pydantic schemas cho reports API — reshape VoC OS (plan 21).

Không field nào chứa text feedback — chỉ con số, id và ids mẫu trong
emerging (shape con của C1, đúng ranh giới PII).

Reshape: `pending_review_count` chết cùng feedback-level HITL; severity/
sentiment/categories đọc từ `ai_analysis` JSONB (pipeline điền).
"""

from datetime import datetime
from enum import IntEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SummaryWindow(IntEnum):
    """Giá trị hợp lệ cho `?days=` — query string đến là `'7'`, IntEnum để
    pydantic coerce được (Literal[7,30,90] thuần sẽ 422 cả giá trị ĐÚNG)."""

    W7 = 7
    W30 = 30
    W90 = 90


class SummaryTotals(BaseModel):
    feedback_count: int
    pii_detected_count: int


class TopCategoryItem(BaseModel):
    category: str
    count: int


class EmergingClusterItem(BaseModel):
    """Shape con của C1 (không `sample_feedback_ids` bắt buộc kiểu riêng)."""

    id: UUID
    name: str
    summary: str
    feedback_count: int
    first_seen: datetime
    last_seen: datetime
    current_count: int
    previous_count: int
    growth_ratio: float
    is_emerging: bool
    is_spike: bool
    suggested_priority: float | None
    sample_feedback_ids: list[UUID] = Field(default_factory=list)


class ReportSummaryOut(BaseModel):
    """Response GET /api/reports/summary — khớp C4 field-by-field.

    Lệch có chủ đích (decisions.md 2026-08-26): `by_sentiment` có 4 key gồm
    `mixed` theo enum thật; `emerging` rỗng khi chưa chạy clustering là hợp lệ.
    """

    generated_at: datetime
    window_days: int
    totals: SummaryTotals
    by_severity: dict[str, int]      # low/medium/high/critical (key luôn đủ)
    by_sentiment: dict[str, int]     # positive/neutral/negative/mixed
    top_categories: list[TopCategoryItem]
    emerging: list[EmergingClusterItem]

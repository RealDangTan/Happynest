"""Pydantic schemas cho reports API — Phase 16 (contract C4).

Không field nào chứa text feedback — chỉ con số, id và ids mẫu trong
emerging (shape con của C1, đúng ranh giới PII).
"""

from datetime import datetime
from enum import Enum, IntEnum
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
    pending_review_count: int
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


class ImpactSummary(BaseModel):
    """Tổng hợp bảng impact_checks — closed-loop phase 20."""

    checks_count: int
    avg_delta_ratio: float | None  # None khi chưa đo insight nào


class ReportKpisOut(BaseModel):
    """Response GET /api/reports/kpis — KPI 3-latency thuần SQL (phase 20).

    Median có thể None khi chưa đủ dữ liệu tạo mốc (vd chưa có draft nào) —
    200 với null là hợp lệ, KHÔNG lỗi "chưa có cụm".
    """

    generated_at: datetime
    time_to_listen_median_s: float | None
    time_to_insight_median_s: float | None
    time_to_action_median_s: float | None
    insights_total: int
    insights_with_action: int
    pct_insight_with_action: float
    hitl_count: int
    auto_count: int
    hitl_share: float
    impact: ImpactSummary

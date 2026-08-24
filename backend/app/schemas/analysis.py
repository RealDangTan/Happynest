"""Pydantic schemas cho analysis runs — plan 09 §3.2.

Progress trả superset của plan ({status, processed_count, total_count, error})
thêm id + mốc thời gian — cần cho UI poll hiển thị timeline. Results TÁI DỤNG
`FeedbackListOut` (đã chứa labels + severity + confidence +
requires_human_review) lọc theo `analysis_run_id`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RunStatus


class RunCreatedOut(BaseModel):
    """Body POST /api/analysis/runs — trả ngay run_id, job chạy nền sau."""

    run_id: UUID


class RunProgressOut(BaseModel):
    """GET /api/analysis/runs/{id} — snapshot tiến độ."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RunStatus
    processed_count: int
    total_count: int
    error: str | None
    started_at: datetime
    completed_at: datetime | None

"""Pydantic schemas cho analysis runs — plan 09 §3.2.

Progress trả superset của plan ({status, processed_count, total_count, error})
thêm id + mốc thời gian — cần cho UI poll hiển thị timeline. Results TÁI DỤNG
`FeedbackListOut` (chứa ai_analysis JSONB) lọc theo `analysis_run_id`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RunStatus


class RunCreatedOut(BaseModel):
    """Body POST /api/analysis/runs — trả ngay run_id, job chạy nền sau."""

    run_id: UUID


class RunProgressOut(BaseModel):
    """GET /api/analysis/runs/{id} — snapshot tiến độ.

    4 field cấu hình (OQ-7, decisions 2026-08-26) là snapshot ĐÃ LƯU trên row
    run lúc tạo — so sánh kết quả giữa các lần chạy khi config đổi. Backward-
    compatible: chỉ thêm field, client cũ bỏ qua.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RunStatus
    processed_count: int
    total_count: int
    error: str | None
    started_at: datetime
    completed_at: datetime | None
    pipeline_version: str
    llm_model: str
    prompt_version: str
    embedding_model: str

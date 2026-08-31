"""Pydantic schemas cho analysis runs — plan 09 §3.2.

Progress trả superset của plan ({status, processed_count, total_count, error})
thêm id + mốc thời gian — cần cho UI poll hiển thị timeline. Results TÁI DỤNG
`FeedbackListOut` (chứa ai_analysis JSONB) lọc theo `analysis_run_id`.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RunStatus


class RunCreatedOut(BaseModel):
    """Body POST /api/analysis/runs — trả ngay run_id, job chạy nền sau."""

    run_id: UUID


class AnalysisScopeIn(BaseModel):
    mode: Literal["selected", "batch"]
    import_id: UUID
    feedback_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.mode == "selected" and not self.feedback_ids:
            raise ValueError("selected mode requires feedback_ids")
        if self.mode == "batch" and self.feedback_ids is not None:
            raise ValueError("batch mode does not accept feedback_ids")
        if self.feedback_ids and len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError("feedback_ids contains duplicate values")
        return self


class AnalysisRunCreateIn(AnalysisScopeIn):
    confirmed_item_count: int = Field(ge=1, le=100)


class AnalysisCostPreviewOut(BaseModel):
    eligible_count: int
    selected_count: int
    remaining_count: int
    estimated_input_tokens: int
    logical_classify_requests: int
    logical_embedding_requests: int
    max_provider_attempts: int
    chunk_size: int


class RunListOut(BaseModel):
    items: list["RunProgressOut"]
    total: int


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
    import_id: UUID | None = None
    mode: str | None = None
    chunk_size: int = 1
    failed_count: int = 0
    cancel_requested_at: datetime | None = None

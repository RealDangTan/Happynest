"""Schemas API agent (phase 19 Task 4) — hợp đồng request/response /api/agent/*.

Bộ lỗi chuẩn C3: 404 run lạ · 409 trạng thái không hợp lệ · 422 body sai
(validator ``edit`` thiếu trường edited_* ném ValueError → FastAPI 422).
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AgentRunCreatedOut(BaseModel):
    run_id: uuid.UUID
    targets: list[uuid.UUID]


class AgentDecisionIn(BaseModel):
    """Resume payload POST /runs/{id}/decision — khớp dict node apply_decision đọc."""

    action: Literal["approve", "edit", "reject"]
    edited_title: str | None = Field(default=None, max_length=255)
    edited_summary: str | None = Field(default=None, max_length=2000)
    edited_suggested_action: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _edit_needs_at_least_one_field(self) -> "AgentDecisionIn":
        if self.action == "edit" and not any(
            (f or "").strip()
            for f in (
                self.edited_title,
                self.edited_summary,
                self.edited_suggested_action,
            )
        ):
            raise ValueError("action='edit' cần ít nhất một trường edited_* khác rỗng")
        return self


class AgentRunStatusOut(BaseModel):
    """GET /runs/{id} — phần động (steps/insights/pending_approval) đọc từ
    snapshot checkpoint; None khi thread chưa khởi động hoặc saver chưa sẵn."""

    run_id: uuid.UUID
    status: str
    total_count: int = 0
    steps_used: int | None = None
    llm_calls_used: int | None = None
    llm_budget: int
    targets: list[uuid.UUID] = Field(default_factory=list)
    insights_created: list[uuid.UUID] = Field(default_factory=list)
    error: str | None = None
    pending_approval: dict[str, Any] | None = None

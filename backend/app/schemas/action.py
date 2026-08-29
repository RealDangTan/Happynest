"""Pydantic schemas cho ACT layer (plan 26) — actions + priority matrix."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BusinessFunction


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    insight_id: UUID
    function: BusinessFunction
    recommendation: str
    rationale: str
    impact: int
    effort: int
    urgency: int
    confidence: float
    priority_score: float
    human_impact: int | None
    human_effort: int | None
    human_urgency: int | None
    override_reason: str | None
    status: str
    created_at: datetime


class ActionsListOut(BaseModel):
    """GET /api/insights/{id}/actions — list + priority matrix grouping (§50)."""

    items: list[ActionOut]
    matrix: dict[str, list[UUID]]  # quadrant → action ids


class ActionGenerateOut(BaseModel):
    actions_created: int
    functions_skipped: list[str]  # relevance < threshold (§47)


class HumanActionIn(BaseModel):
    """POST /api/insights/{id}/actions — human tự thêm action (Gate #3)."""

    function: BusinessFunction
    recommendation: str = Field(min_length=3, max_length=1000)
    rationale: str | None = Field(default=None, max_length=1000)
    impact: int = Field(ge=1, le=10)
    effort: int = Field(ge=1, le=10)
    urgency: int = Field(ge=1, le=10)


class ActionUpdateIn(BaseModel):
    """PATCH /api/actions/{id} — Gate #3 override (VoC OS §51–52).

    Đổi score → ghi human_* (giữ agent value nguyên); đổi recommendation →
    GHI THẲNG (text human sở hữu). priority tính lại deterministic.
    """

    recommendation: str | None = Field(default=None, min_length=3, max_length=1000)
    rationale: str | None = Field(default=None, max_length=1000)
    impact: int | None = Field(default=None, ge=1, le=10)
    effort: int | None = Field(default=None, ge=1, le=10)
    urgency: int | None = Field(default=None, ge=1, le=10)
    override_reason: str | None = Field(default=None, max_length=1000)
    status: str | None = Field(default=None, pattern="^(accepted|rejected)$")

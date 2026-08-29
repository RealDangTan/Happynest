"""Pydantic schemas cho agent API (UNDERSTAND — plan 25) + insights mới."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentRunCreateIn(BaseModel):
    """Body POST /api/agent/runs — question (user) HOẶC signal (system)."""

    product_id: UUID
    question: str = Field(min_length=3, max_length=2000)
    trigger_type: str = Field(default="user_question", pattern="^(user_question|system_signal)$")


class AgentRunCreatedOut(BaseModel):
    run_id: UUID


class AgentRunStatusOut(BaseModel):
    run_id: UUID
    status: str
    error: str | None
    pipeline_version: str
    started_at: datetime
    completed_at: datetime | None
    # Interrupt payload (Gate #2) khi graph đang đậu chờ human — null nếu không
    pending_approval: dict[str, Any] | None = None


class AgentDecisionIn(BaseModel):
    """Body POST /api/agent/runs/{id}/decision — Gate #2 (VoC OS §43)."""

    action: str = Field(pattern="^(approve|edit|investigate_more|reject)$")
    edited_insight: dict[str, Any] | None = None  # {title?, finding?} khi edit
    reason: str | None = Field(default=None, max_length=1000)


class EvidenceRefOut(BaseModel):
    evidence_id: UUID
    statement: str
    source_tool: str


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    run_id: UUID | None
    title: str
    finding: str
    finding_confidence: float
    hypothesis: dict[str, Any] | None
    affected_context: dict[str, Any]
    impact: list[Any]
    limitations: list[Any]
    evidence: list[Any]
    status: str
    created_at: datetime


class InsightsListOut(BaseModel):
    items: list[InsightOut]
    total: int

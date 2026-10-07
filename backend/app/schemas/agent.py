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


class RunProgressOut(BaseModel):
    """Progress điều tra thời gian thực cho FE (đếm từ Evidence/LlmCallLog)."""

    iteration: int
    max_iterations: int
    last_tool: str | None
    llm_calls_used: int
    llm_budget: int
    evidence_count: int


class AgentTraceRowOut(BaseModel):
    """1 dòng trace metadata-only (HAX G4/G16) — KHÔNG prompt/response."""

    call_type: str
    status: str  # "ok" | "error"
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    model: str
    prompt_version: str
    error: str | None  # tối đa 200 ký tự, null nếu ok
    created_at: datetime


class AgentTraceOut(BaseModel):
    run_id: UUID
    items: list[AgentTraceRowOut]


class AgentRunStatusOut(BaseModel):
    run_id: UUID
    status: str
    error: str | None
    pipeline_version: str
    started_at: datetime
    completed_at: datetime | None
    # Interrupt payload (Gate #2) khi graph đang đậu chờ human — null nếu không
    pending_approval: dict[str, Any] | None = None
    progress: RunProgressOut | None = None


class AgentDecisionIn(BaseModel):
    """Body POST /api/agent/runs/{id}/decision — Gate #2 (VoC OS §43)."""

    action: str = Field(pattern="^(approve|edit|investigate_more|reject)$")
    edited_insight: dict[str, Any] | None = None  # {title?, finding?} khi edit
    reason: str | None = Field(default=None, max_length=1000)


class InsightUpdateIn(BaseModel):
    """Body PATCH /api/insights/{id} — sửa trực tiếp title/finding (pm)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    finding: str | None = Field(default=None, min_length=1)


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

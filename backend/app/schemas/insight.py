"""Pydantic schemas insights — Phase 15.

- `InsightDraft`: schema structured-output LLM cho 1 cụm (chat_structured Mode A
  strict — KHÔNG dùng default cho field nào, strict json_schema không cho phép).
  Server whitelist-filter `evidence_feedback_ids` sau khi nhận (services/insight).
- `InsightOut`/`EvidenceOut`: response GET /api/insights khớp contract C2.
- `InsightsRunOut`: response POST /api/insights/run khớp C6; field `skipped`
  ngoài hợp đồng được phép (C6 không cấm field bổ sung — plan Step 3.1).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InsightDraft(BaseModel):
    """Đầu ra LLM cho một cụm — dẫn chứng chỉ là ĐỀ XUẤT tới khi server lọc."""

    title: str = Field(max_length=120)
    summary: str = Field(max_length=600)
    suggested_action: str = Field(max_length=400)
    evidence_feedback_ids: list[UUID]


class EvidenceOut(BaseModel):
    feedback_id: UUID
    snippet: str          # cắt từ sanitized_content — không bao giờ raw (C2)
    severity: str | None = None
    created_at: datetime


class InsightOut(BaseModel):
    """Một insight trong GET /api/insights — khớp C2 field-by-field."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID | None
    title: str
    summary: str
    suggested_action: str
    review_status: str
    # không nằm trên ORM — route mở rộng từ evidence_ids JSONB (C2)
    evidence: list[EvidenceOut] = Field(default_factory=list)


class InsightsListOut(BaseModel):
    items: list[InsightOut]


class InsightsRunOut(BaseModel):
    """Response POST /api/insights/run — C6 + skipped ngoài hợp đồng."""

    insights_generated: int
    duration_ms: int
    skipped: int = 0

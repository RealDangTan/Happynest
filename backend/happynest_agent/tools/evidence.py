"""Tool `fetch_evidence_quotes` — bằng chứng cho router/synthesizer (phase 18 Task 4).

Snippet cắt TỪ `sanitized_content` — raw_content KHÔNG BAO GIỜ ra khỏi biên PII
(canary test trong tests/test_agent_tools_metrics.py là khuôn cho mọi tool sau).
Row chưa sanitize bị loại. Thứ tự: confidence DESC NULLS LAST, created_at DESC.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from happynest_agent.tools.base import ToolInput, ToolSpec
from app.models.feedback import Feedback

_SNIPPET_LEN = 200


class EvidenceIn(ToolInput):
    cluster_id: uuid.UUID
    limit: int = Field(8, ge=1, le=8)


class Quote(BaseModel):
    feedback_id: uuid.UUID
    snippet: str  # ≤200 ký tự từ sanitized_content
    severity: str | None
    created_at: datetime


class EvidenceQuotesOut(BaseModel):
    quotes: list[Quote]


def execute(db: Session, params: EvidenceIn) -> EvidenceQuotesOut:
    rows = db.scalars(
        select(Feedback)
        .where(
            Feedback.cluster_id == params.cluster_id,
            Feedback.sanitized_content.is_not(None),
        )
        .order_by(
            Feedback.confidence.desc().nullslast(),
            Feedback.created_at.desc(),
        )
        .limit(params.limit)
    ).all()

    return EvidenceQuotesOut(
        quotes=[
            Quote(
                feedback_id=fb.id,
                snippet=fb.sanitized_content[:_SNIPPET_LEN],
                severity=fb.severity.value if hasattr(fb.severity, "value") else fb.severity,
                created_at=fb.created_at,
            )
            for fb in rows
        ]
    )


SPEC = ToolSpec(
    name="fetch_evidence_quotes",
    description=(
        "Fetch up to 8 short evidence snippets from sanitized feedback content "
        "of one cluster, most confident first."
    ),
    input_model=EvidenceIn,
    output_model=EvidenceQuotesOut,
)

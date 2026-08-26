"""Tool `retrieve_similar_insights` — precedent kNN trên insights.embedding
(phase 18 Task 5).

Brute-force `<=>` như `/feedbacks/{id}/similar` (phase 08) — KHÔNG ANN index
(dataset ≤1500). Mỗi match kèm `human_decision` từ dòng insight_reviews MỚI
NHẤT (JOIN-LATERAL) — điểm "precedent có kèm phán quyết người" của thiết kế.
Query_text được embed 1 lần; text nhúng là sanitized-safe (router gửi mô tả
cụm, không phải raw content).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from happynest_agent.tools.base import ToolInput, ToolSpec
from app.services.embedder import embed_one


class PrecedentsIn(ToolInput):
    query_text: str
    top_k: int = Field(3, ge=1, le=10)


class HumanDecision(BaseModel):
    action: str
    reason: str | None = None


class PrecedentMatch(BaseModel):
    insight_id: uuid.UUID
    title: str
    summary: str  # ≤300 ký tự
    similarity: float
    human_decision: HumanDecision | None = None


class PrecedentsOut(BaseModel):
    matches: list[PrecedentMatch]


def execute(db: Session, params: PrecedentsIn) -> PrecedentsOut:
    query_vec = "[" + ",".join(f"{float(x)!r}" for x in embed_one(params.query_text)) + "]"

    rows = db.execute(
        text(
            """
            SELECT i.id::text          AS id,
                   i.title             AS title,
                   LEFT(i.summary, 300) AS summary,
                   1 - (i.embedding <=> CAST(:query_vec AS vector)) AS similarity,
                   r.action            AS human_action,
                   r.reason            AS human_reason
            FROM insights i
            LEFT JOIN LATERAL (
                SELECT action, reason
                FROM insight_reviews
                WHERE insight_id = i.id
                ORDER BY created_at DESC
                LIMIT 1
            ) r ON true
            WHERE i.embedding IS NOT NULL
            ORDER BY i.embedding <=> CAST(:query_vec AS vector)
            LIMIT :k
            """
        ),
        {"query_vec": query_vec, "k": params.top_k},
    ).mappings()

    matches = [
        PrecedentMatch(
            insight_id=uuid.UUID(row["id"]),
            title=row["title"],
            summary=row["summary"] or "",
            similarity=float(row["similarity"]),
            human_decision=(
                HumanDecision(action=row["human_action"], reason=row["human_reason"])
                if row["human_action"] is not None
                else None
            ),
        )
        for row in rows
    ]
    return PrecedentsOut(matches=matches)


SPEC = ToolSpec(
    name="retrieve_similar_insights",
    description=(
        "Find the most similar past insights by embedding distance, each with "
        "the latest human decision when one exists."
    ),
    input_model=PrecedentsIn,
    output_model=PrecedentsOut,
)

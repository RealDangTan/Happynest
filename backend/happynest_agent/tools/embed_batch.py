"""Tool `embed_batch` — wrap mỏng quanh services/embedder (phase 18 Task 2).

Cùng predicate resume phase 09 như classify_batch; row đã có vector → skipped.
Embedding tính từ `sanitized_content` (PII boundary) và luôn ghi đủ triplet
embedding/embedding_model/embedding_dim qua store_embedding.
"""

from __future__ import annotations

import uuid

from openai import APIError
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from happynest_agent.tools.base import ToolInput, ToolSpec
from app.models.feedback import Feedback
from app.services.embedder import EmbeddingDimError, embed_one, store_embedding
from app.services.presidio_service import sanitize

_ITEM_ERRORS = (EmbeddingDimError, APIError)


class EmbedBatchIn(ToolInput):
    limit: int = Field(50, ge=1, le=500)


class EmbedBatchOut(BaseModel):
    processed: int
    failed: int
    skipped_ids: list[uuid.UUID]


def execute(db: Session, params: EmbedBatchIn) -> EmbedBatchOut:
    candidates = db.scalars(
        select(Feedback)
        .where(or_(Feedback.analysis_run_id.is_(None), Feedback.categories.is_(None)))
        .order_by(Feedback.created_at, Feedback.id)
        .limit(params.limit)
    ).all()

    processed = failed = 0
    skipped: list[uuid.UUID] = []
    for fb in candidates:
        if fb.embedding is not None:
            skipped.append(fb.id)
            continue
        try:
            if fb.sanitized_content is None:
                result = sanitize(fb.raw_content)
                fb.sanitized_content = result.sanitized_text
                fb.pii_detected = result.pii_detected
                fb.pii_entities = [e.model_dump() for e in result.entities]
            store_embedding(db, fb, embed_one(fb.sanitized_content))
            db.commit()
            processed += 1
        except _ITEM_ERRORS:
            db.rollback()
            failed += 1
    return EmbedBatchOut(processed=processed, failed=failed, skipped_ids=skipped)


SPEC = ToolSpec(
    name="embed_batch",
    description=(
        "Compute and store embeddings for up to `limit` feedback rows that are "
        "missing vectors yet."
    ),
    input_model=EmbedBatchIn,
    output_model=EmbedBatchOut,
)

"""Tool `classify_batch` — wrap mỏng quanh services/classifier (phase 18 Task 2).

KHÔNG viết lại logic classify: chọn row theo predicate resume phase 09
(`analysis_run_id IS NULL OR categories IS NULL`), gọi classifier tuần tự với
passthrough feedback_id/analysis_run_id vào llm_call_logs, commit TỪNG item
(crash giữa chừng không mất tiến độ — cùng philosophy runner).
Row đã có labels trong danh sách chọn → skipped (không tốn LLM).
Item lỗi KHÔNG chặn item kế.
"""

from __future__ import annotations

import uuid

from openai import APIError
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from happynest_agent.tools.base import ToolInput, ToolSpec
from app.models.enums import ReviewStatus
from app.models.feedback import Feedback
from app.services.classifier import (
    classify_feedback,
    compute_requires_human_review,
)
from app.services.llm_client import LLMStructureError
from app.services.presidio_service import sanitize

_ITEM_ERRORS = (LLMStructureError, APIError)


class ClassifyBatchIn(ToolInput):
    limit: int = Field(50, ge=1, le=500)


class ClassifyBatchOut(BaseModel):
    processed: int
    failed: int
    skipped_ids: list[uuid.UUID]


def execute(db: Session, params: ClassifyBatchIn) -> ClassifyBatchOut:
    candidates = db.scalars(
        select(Feedback)
        .where(or_(Feedback.analysis_run_id.is_(None), Feedback.categories.is_(None)))
        .order_by(Feedback.created_at, Feedback.id)
        .limit(params.limit)
    ).all()

    processed = failed = 0
    skipped: list[uuid.UUID] = []
    for fb in candidates:
        # Marker "đã xử lý" của pipeline là categories NOT NULL (runner §7).
        if fb.categories is not None:
            skipped.append(fb.id)
            continue
        try:
            # Row legacy chưa sanitize → làm tại chỗ (mirror _process_item);
            # sanitized_content là thứ duy nhất ra khỏi biên PII.
            if fb.sanitized_content is None:
                result = sanitize(fb.raw_content)
                fb.sanitized_content = result.sanitized_text
                fb.pii_detected = result.pii_detected
                fb.pii_entities = [e.model_dump() for e in result.entities]

            classification = classify_feedback(
                fb.sanitized_content,
                feedback_id=fb.id,
                analysis_run_id=params.run_id,
            )
            fb.categories = classification.categories
            fb.ai_issue = classification.ai_issue
            fb.sentiment = classification.sentiment
            fb.severity = classification.severity
            fb.confidence = classification.confidence
            fb.safety_issue = classification.safety_issue
            fb.requires_human_review = compute_requires_human_review(
                classification, pii_detected=fb.pii_detected
            )
            fb.review_status = (
                ReviewStatus.pending
                if fb.requires_human_review
                else ReviewStatus.unreviewed
            )
            db.commit()
            processed += 1
        except _ITEM_ERRORS:
            db.rollback()
            failed += 1
    return ClassifyBatchOut(processed=processed, failed=failed, skipped_ids=skipped)


SPEC = ToolSpec(
    name="classify_batch",
    description=(
        "Classify up to `limit` feedback rows that have no labels yet using the "
        "production LLM classifier."
    ),
    input_model=ClassifyBatchIn,
    output_model=ClassifyBatchOut,
)

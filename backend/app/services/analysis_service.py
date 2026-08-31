"""Import-scoped analysis selection and budget receipts (phase 28)."""

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.feedback import Feedback
from app.schemas.analysis import AnalysisCostPreviewOut, AnalysisScopeIn


class SelectionChangedError(ValueError):
    """The eligible rows no longer match the user's confirmed receipt."""


def build_cost_receipt(
    *,
    mode: str,
    texts: list[str],
    eligible_count: int,
    chunk_size: int,
) -> AnalysisCostPreviewOut:
    selected = len(texts)
    logical = selected if mode == "selected" else math.ceil(selected / chunk_size)
    # Classifier fallback: max 3 attempts; embedder: max 4 attempts.
    max_attempts = logical * 7
    return AnalysisCostPreviewOut(
        eligible_count=eligible_count,
        selected_count=selected,
        remaining_count=max(eligible_count - selected, 0),
        estimated_input_tokens=sum(max(math.ceil(len(text) / 4), 1) for text in texts),
        logical_classify_requests=logical,
        logical_embedding_requests=logical,
        max_provider_attempts=max_attempts,
        chunk_size=1 if mode == "selected" else chunk_size,
    )


def select_eligible_feedback(
    db: Session,
    scope: AnalysisScopeIn,
    *,
    for_update: bool = False,
) -> tuple[list[Feedback], int]:
    """Resolve exactly one import's pending, unclaimed rows."""
    conditions = (
        Feedback.import_id == scope.import_id,
        Feedback.ai_analysis.is_(None),
        Feedback.analysis_run_id.is_(None),
    )
    eligible_count = int(
        db.scalar(select(func.count()).select_from(Feedback).where(*conditions)) or 0
    )
    stmt = select(Feedback).where(*conditions)
    if scope.mode == "selected":
        stmt = stmt.where(Feedback.id.in_(scope.feedback_ids or []))
    stmt = stmt.order_by(Feedback.occurred_at, Feedback.id)
    if scope.mode == "batch":
        stmt = stmt.limit(get_settings().ANALYSIS_MAX_ITEMS_PER_RUN)
    if for_update:
        stmt = stmt.with_for_update(skip_locked=True)
    rows = list(db.scalars(stmt).all())
    if scope.mode == "selected" and len(rows) != len(scope.feedback_ids or []):
        raise SelectionChangedError("selection_changed")
    return rows, eligible_count


def preview_analysis(db: Session, scope: AnalysisScopeIn) -> AnalysisCostPreviewOut:
    rows, eligible_count = select_eligible_feedback(db, scope)
    return build_cost_receipt(
        mode=scope.mode,
        texts=[row.feedback_text or "" for row in rows],
        eligible_count=eligible_count,
        chunk_size=get_settings().ANALYSIS_BATCH_SIZE,
    )

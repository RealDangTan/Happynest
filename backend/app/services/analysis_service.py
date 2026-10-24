"""Import-scoped analysis selection and budget receipts (phase 28 + plan 32)."""

import math
import uuid

from sqlalchemy import func, null, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.feedback import Feedback
from app.schemas.analysis import AnalysisCostPreviewOut, AnalysisScopeIn

#: Scope DB của selection: chỉ (id, feedback_text). Preview chỉ cần text để
#: estimate token; create dùng id để claim. KHÔNG select entity đầy đủ — cột
#: `embedding` 1536-d (~19KB/row) khiến preview/claim kéo vô số MB vô nghĩa qua
#: WAN tới Supabase (2026-10-23: vault preview chậm thấy rõ vì lỗi này).
EligibleRow = tuple[uuid.UUID, str | None]


class SelectionChangedError(ValueError):
    """The eligible rows no longer match the user's confirmed receipt."""


def build_cost_receipt(
    *,
    mode: str,
    texts: list[str],
    eligible_count: int,
    chunk_size: int,
) -> AnalysisCostPreviewOut:
    """v4 singular (owner 2026-10-22): mỗi item = 1 enrich call + 1 embed call —
    `mode`/`chunk_size` không còn đổi cách tính (chunk_size chỉ còn snapshot)."""
    selected = len(texts)
    # Enricher fallback/jev retry: tối đa 3 attempts; embedder: tối đa 4.
    max_attempts = selected * 7
    return AnalysisCostPreviewOut(
        eligible_count=eligible_count,
        selected_count=selected,
        remaining_count=max(eligible_count - selected, 0),
        estimated_input_tokens=sum(max(math.ceil(len(text) / 4), 1) for text in texts),
        logical_classify_requests=selected,
        logical_embedding_requests=selected,
        max_provider_attempts=max_attempts,
        chunk_size=1,
    )


def select_eligible_feedback(
    db: Session,
    scope: AnalysisScopeIn,
    *,
    for_update: bool = False,
) -> tuple[list[EligibleRow], int]:
    """Resolve exactly one import's pending, unclaimed rows — LEAN (id, text).

    "Pending, unclaimed" = `ai_analysis IS NULL AND analysis_run_id IS NULL`.
    Nhãn cũ (đã analyzed, kể cả UNCATEGORIZED) không bao giờ eligible — vòng
    re-run sau taxonomy update phải qua `reset_uncategorized` trước."""
    conditions = (
        Feedback.import_id == scope.import_id,
        Feedback.ai_analysis.is_(None),
        Feedback.analysis_run_id.is_(None),
    )
    eligible_count = int(
        db.scalar(select(func.count()).select_from(Feedback).where(*conditions)) or 0
    )
    stmt = select(Feedback.id, Feedback.feedback_text).where(*conditions)
    if scope.mode == "selected":
        stmt = stmt.where(Feedback.id.in_(scope.feedback_ids or []))
    stmt = stmt.order_by(Feedback.occurred_at, Feedback.id)
    if scope.mode == "batch":
        stmt = stmt.limit(get_settings().ANALYSIS_MAX_ITEMS_PER_RUN)
    if for_update:
        stmt = stmt.with_for_update(skip_locked=True)
    rows = [(row_id, text) for row_id, text in db.execute(stmt).all()]
    if scope.mode == "selected" and len(rows) != len(scope.feedback_ids or []):
        raise SelectionChangedError("selection_changed")
    return rows, eligible_count


def preview_analysis(db: Session, scope: AnalysisScopeIn) -> AnalysisCostPreviewOut:
    rows, eligible_count = select_eligible_feedback(db, scope)
    return build_cost_receipt(
        mode=scope.mode,
        texts=[text or "" for _, text in rows],
        eligible_count=eligible_count,
        chunk_size=get_settings().ANALYSIS_BATCH_SIZE,
    )


def reset_uncategorized(db: Session, product_id: uuid.UUID) -> int:
    """Clear `ai_analysis` + `analysis_run_id` của rows uncategorized (plan 32
    — taxonomy v2 được apply rồi, enrich lại theo nhãn mới).

    CHỈ đụng nhãn dẫn xuất: raw_content/feedback_text/embedding GIỮ NGUYÊN
    (embedding tính từ text — vẫn hợp lệ). Trả số row được clear.

    ⚠️ `ai_analysis` PHẢI là SQL NULL (qua `null()`, không phải bind None):
    psycopg3 + JSONB serialize None thành JSON `null` — `IS NULL` của mọi
    filter pending/eligible KHÔNG bao giờ khớp → vault "0 pending" vĩnh viễn
    dù FE hiển thị Pending (bug thật 2026-10-23, 30/32 row TEST2 dính)."""
    result = db.execute(
        update(Feedback)
        .where(
            Feedback.product_id == product_id,
            Feedback.ai_analysis["uncategorized"].astext == "true",
        )
        .values(ai_analysis=null(), analysis_run_id=null())
    )
    db.commit()
    return int(result.rowcount or 0)

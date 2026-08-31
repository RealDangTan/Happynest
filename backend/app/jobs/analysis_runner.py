"""Analysis runner — batch pipeline idempotent/resumable (plan 09; reshape plan 21).

Với mỗi feedback CHƯA xử lý: claim → classify (từ `feedback_text`) →
ghi `ai_analysis` JSONB → embed → UPDATE row. **Commit từng item** —
crash giữa chừng không mất tiến độ.

Hợp đồng khóa (§7):
    def run_analysis(run_id: uuid.UUID) -> None

Semantics resume — QUYẾT ĐỊNH ĐÃ GHI docs/decisions.md 2026-08-24 (giữ nguyên
qua reshape):
- Chọn **resume cùng run** (gọi lại `run_analysis(run_id)` trên run còn
  `running|failed`), KHÔNG tạo run mới. Một row run = một lô logic toàn bộ,
  `processed_count` monotonic xuyên qua crash.
- Row "chưa xử lý" = `analysis_run_id IS NULL` (chưa ai claim) **HOẶC**
  (`analysis_run_id = :run_id` và `ai_analysis IS NULL` — đã claim nhưng crash
  trước khi classify xong). Marker "đã xử lý" là `ai_analysis IS NOT NULL`:
  classifier luôn ghi đủ bộ nhãn trong cùng commit, all-or-nothing đáng tin.
- Item đã claim bởi run KHÁC không bao giờ bị lấy — không giành công việc.
- Item lỗi item-level (`LLMStructureError`, embedding fail) bị bỏ qua TRONG
  cùng lượt chạy (không retry in-loop); gọi lại `run_analysis(run_id)` lần sau
  sẽ nhặt lại đúng những item classify-chưa-xong đó.

Reshape 2026-08-28: output classify ghi `ai_analysis` JSONB (topics/sentiment/
severity/...) thay cho các cột phẳng; logic review_status/few-shot đã chết cùng
feedback-level HITL — plan 23 sẽ đổi classifier sang taxonomy-aware.

⚠️ PII boundary: log chỉ chứa id + loại lỗi — KHÔNG log raw/feedback_text.
Exception text đi vào `analysis_runs.error` có thể chứa JSON do MODEL sinh ra
TRÊN text đã sanitize → vẫn nằm trong biên an toàn.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from openai import APIError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.models.feedback import Feedback
from app.services import taxonomy_service
from app.services.classifier import (
    PROMPT_VERSION,
    classify_feedback,
    classify_feedback_batch,
)
from app.services.embedder import (
    EmbeddingDimError,
    embed_one,
    embed_texts,
    store_embedding,
)
from app.services.llm_client import LLMStructureError
from app.services.presidio_service import sanitize

logger = logging.getLogger(__name__)

#: Version pipeline snapshot vào analysis_runs khi tạo run — tăng khi đổi
#: cấu trúc pipeline (thứ tự bước, shape output…) để so sánh kết quả A/B.
#: v2 = reshape VoC OS (output ai_analysis JSONB).
PIPELINE_VERSION = "v2"

#: Lỗi item-level: batch KHÔNG chết, chỉ ghi tóm tắt rồi bỏ qua item.
_ITEM_ERRORS = (LLMStructureError, EmbeddingDimError, APIError)

_ERROR_SUMMARY_MAX = 2000


def _pick_next(db: Session, run_id: uuid.UUID, attempted: set[uuid.UUID]):
    """Row kế tiếp chưa xử lý (xem semantics resume đầu module).

    `attempted` = id đã thử trong LƯỢT gọi hiện tại — loại ra để item vừa lỗi
    không bị chọn lại ngay (chặn vòng lặp vô hạn trong một lượt chạy).
    """
    stmt = select(Feedback).where(
        Feedback.analysis_run_id == run_id,
        Feedback.ai_analysis.is_(None),
    )
    if attempted:
        stmt = stmt.where(Feedback.id.not_in(attempted))
    return db.scalars(
        stmt.order_by(Feedback.occurred_at, Feedback.id).limit(1)
    ).first()


def _pick_chunk(
    db: Session,
    run_id: uuid.UUID,
    attempted: set[uuid.UUID],
    chunk_size: int,
) -> list[Feedback]:
    stmt = select(Feedback).where(
        Feedback.analysis_run_id == run_id,
        Feedback.ai_analysis.is_(None),
    )
    if attempted:
        stmt = stmt.where(Feedback.id.not_in(attempted))
    return list(
        db.scalars(
            stmt.order_by(Feedback.occurred_at, Feedback.id).limit(chunk_size)
        ).all()
    )


def _release_unprocessed(db: Session, run_id: uuid.UUID) -> None:
    db.execute(
        update(Feedback)
        .where(
            Feedback.analysis_run_id == run_id,
            Feedback.ai_analysis.is_(None),
        )
        .values(analysis_run_id=None)
    )


def _classification_json(classification) -> dict:
    return {
        "topics": classification.categories,
        "ai_issue": classification.ai_issue.value if classification.ai_issue else None,
        "sentiment": classification.sentiment.value,
        "severity": classification.severity.value,
        "safety_issue": classification.safety_issue,
        "confidence": classification.confidence,
        "rationale": classification.rationale,
        "analysis_version": "classifier-v2-taxonomy",
    }


def _process_item(
    db: Session,
    run: AnalysisRun,
    fb: Feedback,
    taxonomy_cache: dict[uuid.UUID, list[str]],
) -> None:
    """Classify + ghi `ai_analysis` + emerging theme + embed MỘT item — KHÔNG
    commit (caller gộp commit với processed_count). Raise item-level error để
    caller ghi tóm tắt."""
    # 1. Text vào classifier PHẢI đã sanitize; row legacy chưa sanitize → làm tại chỗ.
    if fb.feedback_text is None:
        result = sanitize(fb.raw_content)
        fb.feedback_text = result.sanitized_text
        fb.pii_detected = result.pii_detected
        fb.pii_entities = [e.model_dump() for e in result.entities]

    # 2. Taxonomy của product (cache per run — plan 23: classify ưu tiên khớp
    # taxonomy; topic lạ accumulate vào emerging theme queue).
    if fb.product_id not in taxonomy_cache:
        taxonomy_cache[fb.product_id] = taxonomy_service.get_taxonomy_names(
            db, fb.product_id
        )

    # 3. Classify (LLM) + trace metadata gắn feedback/run vào llm_call_logs.
    classification = classify_feedback(
        fb.feedback_text,
        taxonomy_names=taxonomy_cache[fb.product_id],
        feedback_id=fb.id,
        analysis_run_id=run.id,
    )

    # 4. Ghi ai_analysis JSONB all-or-nothing (cùng 1 commit) — đây là marker
    # "đã xử lý". safety_issue gộp vào JSONB (không còn cột riêng).
    fb.ai_analysis = _classification_json(classification)

    # 5. Emerging theme flow (VoC OS §21): topic lạ → accumulate vào hàng chờ
    # pending_review — KHÔNG tự mutate canonical taxonomy.
    taxonomy_service.accumulate_emerging(
        db,
        fb.product_id,
        classification.categories,
        taxonomy_names=taxonomy_cache[fb.product_id],
    )

    # 6. Embedding từ feedback_text (PII boundary) — luôn kèm model + dim.
    vector = embed_one(fb.feedback_text)
    store_embedding(db, fb, vector)


def _process_chunk(
    db: Session,
    run: AnalysisRun,
    rows: list[Feedback],
    taxonomy_cache: dict[uuid.UUID, list[str]],
) -> None:
    """One classify call + one embedding-array call for a true batch chunk."""
    for fb in rows:
        if fb.feedback_text is None:
            result = sanitize(fb.raw_content)
            fb.feedback_text = result.sanitized_text
            fb.pii_detected = result.pii_detected
            fb.pii_entities = [entity.model_dump() for entity in result.entities]
        if fb.product_id not in taxonomy_cache:
            taxonomy_cache[fb.product_id] = taxonomy_service.get_taxonomy_names(
                db, fb.product_id
            )
    taxonomy_names = taxonomy_cache[rows[0].product_id]
    classified = classify_feedback_batch(
        [(fb.id, fb.feedback_text or "") for fb in rows],
        taxonomy_names=taxonomy_names,
        analysis_run_id=run.id,
    )
    vectors = embed_texts([fb.feedback_text or "" for fb in rows])
    if len(vectors) != len(rows):
        raise EmbeddingDimError("Embedding batch response count mismatch.")
    for fb, vector in zip(rows, vectors, strict=True):
        classification = classified[fb.id]
        fb.ai_analysis = _classification_json(classification)
        taxonomy_service.accumulate_emerging(
            db,
            fb.product_id,
            classification.categories,
            taxonomy_names=taxonomy_names,
        )
        store_embedding(db, fb, vector)


def run_analysis(run_id: uuid.UUID) -> None:
    """Chạy batch cho `run_id` (idempotent — gọi lại được sau crash, xem header).

    Session RIÊNG của job (không dùng session request). Lỗi ngoài `_ITEM_ERRORS`
    (bug code, DB chết…) → đánh dấu run `failed` rồi nuốt để BackgroundTasks
    không nổ process; caller test vẫn đọc được state run sau crash.
    """
    started = time.perf_counter()
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            logger.error("run_analysis: run %s không tồn tại — bỏ qua.", run_id)
            return

        attempted: set[uuid.UUID] = set()
        errors: list[str] = []
        processed_this_pass = 0
        taxonomy_cache: dict[uuid.UUID, list[str]] = {}

        try:
            while True:
                db.refresh(run)
                if run.cancel_requested_at is not None:
                    _release_unprocessed(db, run.id)
                    run.status = RunStatus.cancelled
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    return

                rows = (
                    [_pick_next(db, run.id, attempted)]
                    if run.mode != "batch"
                    else _pick_chunk(db, run.id, attempted, run.chunk_size)
                )
                rows = [row for row in rows if row is not None]
                if not rows:
                    break

                try:
                    if run.mode == "batch":
                        _process_chunk(db, run, rows, taxonomy_cache)
                    else:
                        _process_item(db, run, rows[0], taxonomy_cache)
                except _ITEM_ERRORS as exc:
                    db.rollback()
                    failed_ids = [row.id for row in rows]
                    db.execute(
                        update(Feedback)
                        .where(Feedback.id.in_(failed_ids))
                        .values(analysis_run_id=None)
                    )
                    attempted.update(failed_ids)
                    run = db.get(AnalysisRun, run_id)
                    run.failed_count += len(failed_ids)
                    short = f"{','.join(map(str, failed_ids))}: {type(exc).__name__}: {exc}"
                    errors.append(short[:300])
                    logger.warning("chunk %s lỗi (unclaim): %s", failed_ids, type(exc).__name__)
                    # Fallback plan §6: >50% BATCH lỗi (mẫu số = total_count
                    # snapshot lúc tạo run) → dừng sớm, status failed.
                    if run.failed_count * 2 > max(run.total_count, 1):
                        _release_unprocessed(db, run.id)
                        run.error = _join_errors(errors)
                        run.status = RunStatus.failed
                        run.completed_at = datetime.now(timezone.utc)
                        db.commit()
                        logger.error(
                            "run %s dừng sớm: %d/%d item lỗi.", run.id, len(errors), run.total_count
                        )
                        return
                    continue

                attempted.update(row.id for row in rows)
                run.processed_count += len(rows)
                db.commit()
                processed_this_pass += len(rows)

            run.status = RunStatus.completed
            run.completed_at = datetime.now(timezone.utc)
            # Ghi tóm tắt lỗi item-level NẾU CÓ ở lượt này; hoàn tất sạch (kể cả
            # sau khi heal lỗi crash lượt trước) → error=None.
            run.error = _join_errors(errors) if errors else None
            db.commit()
        except Exception as exc:  # noqa: BLE001 — crash thật sự của batch
            db.rollback()
            run.status = RunStatus.failed
            run.error = f"{type(exc).__name__}: {exc}"[:_ERROR_SUMMARY_MAX]
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.exception("run %s crashed sau %d item:", run.id, processed_this_pass)
            return

    logger.info(
        "run %s hoàn tất: +%d item trong %.1fs",
        run_id,
        processed_this_pass,
        time.perf_counter() - started,
    )


def _join_errors(errors: list[str]) -> str:
    summary = " | ".join(errors)
    return summary[:_ERROR_SUMMARY_MAX]


__all__ = ["PIPELINE_VERSION", "PROMPT_VERSION", "run_analysis"]

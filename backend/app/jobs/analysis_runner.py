"""Analysis runner — batch pipeline idempotent/resumable (plan 09; v3 plan 32).

Với mỗi feedback CHƯA xử lý: claim → sanitize nếu cần → ENRICH (từ
`feedback_text`) → ghi `ai_analysis` JSONB → embed → UPDATE row. **Commit từng
item** — crash giữa chừng không mất tiến độ.

Hợp đồng khóa (§7):
    def run_analysis(run_id: uuid.UUID) -> None

Semantics resume — QUYẾT ĐỊNH ĐÃ GHI docs/decisions.md 2026-08-24 (giữ nguyên
qua các reshape):
- Chọn **resume cùng run** (gọi lại `run_analysis(run_id)` trên run còn
  `running|failed`), KHÔNG tạo run mới. Một row run = một lô logic toàn bộ,
  `processed_count` monotonic xuyên qua crash.
- Row "chưa xử lý" = `analysis_run_id IS NULL` (chưa ai claim) **HOẶC**
  (`analysis_run_id = :run_id` và `ai_analysis IS NULL` — đã claim nhưng crash
  trước khi enrich xong). Marker "đã xử lý" là `ai_analysis IS NOT NULL`:
  enricher luôn ghi đủ bộ nhãn trong cùng commit, all-or-nothing đáng tin.
- Item đã claim bởi run KHÁC không bao giờ bị lấy — không giành công việc.
- Item lỗi item-level (`LLMStructureError`, embedding fail) bị bỏ qua TRONG
  cùng lượt chạy (không retry in-loop) và được RELEASE (`analysis_run_id=None`)
  — một run MỚI (claim mới qua `select_eligible_feedback`) sẽ nhặt lại. Item
  crash GIỮA commit (claim còn nguyên, `ai_analysis` NULL) mới được resume
  cùng run nhặt lại.

Re-spec Listen 2026-10-07 (plans 31–32): enricher v3 CLOSED-SET — topics CHỈ
từ Active Taxonomy (slug), confidence < floor → UNCATEGORIZED giữ lại;
**auto-emerging per-record ĐÃ BỎ** (accumulate_emerging không còn gọi — topic
mới chỉ đến từ GPT recommend batch + human apply, plan 34).

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
from app.models.product import Product
from app.services import taxonomy_service
from app.services.embedder import (
    EmbeddingDimError,
    embed_one,
    embed_texts,
    store_embedding,
)
from app.services.enricher import (
    PROMPT_VERSION,
    enrich_feedback,
    enrich_feedback_batch,
)
from app.services.llm_client import LLMStructureError
from app.services.presidio_service import sanitize

logger = logging.getLogger(__name__)

#: Version pipeline snapshot vào analysis_runs khi tạo run — tăng khi đổi
#: cấu trúc pipeline (thứ tự bước, shape output…) để so sánh kết quả A/B.
#: v3 = re-spec Listen (closed-set topics + UNCATEGORIZED + emotions/intent).
PIPELINE_VERSION = "v3"

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


def _taxonomy_labels(db: Session, product_id: uuid.UUID) -> list[tuple[str, str]]:
    """(slug, name) Active Taxonomy của product — runner version (không cache
    tự quản; runner giữ cache ngoài qua dict)."""
    return taxonomy_service.get_taxonomy_labels(db, product_id)


def _process_item(
    db: Session,
    run: AnalysisRun,
    fb: Feedback,
    taxonomy_cache: dict[uuid.UUID, list[tuple[str, str]]],
    version_cache: dict[uuid.UUID, int],
) -> None:
    """Sanitize + enrich + ghi `ai_analysis` + embed MỘT item — KHÔNG commit
    (caller gộp commit với processed_count). Raise item-level error để caller
    ghi tóm tắt."""
    # 1. Text vào enricher PHẢI đã sanitize; row legacy chưa sanitize → làm tại chỗ.
    if fb.feedback_text is None:
        result = sanitize(fb.raw_content)
        fb.feedback_text = result.sanitized_text
        fb.pii_detected = result.pii_detected
        fb.pii_entities = [e.model_dump() for e in result.entities]

    # 2. Active Taxonomy (slug, name) + taxonomy_version — cache per run.
    if fb.product_id not in taxonomy_cache:
        taxonomy_cache[fb.product_id] = _taxonomy_labels(db, fb.product_id)
    if fb.product_id not in version_cache:
        version_cache[fb.product_id] = (
            db.scalar(select(Product.taxonomy_version).where(Product.id == fb.product_id))
            or 1
        )

    # 3. Enrich (JEV-role LLM backend) + trace metadata vào llm_call_logs.
    fb.ai_analysis = enrich_feedback(
        fb.feedback_text,
        taxonomy_cache[fb.product_id],
        taxonomy_version=version_cache[fb.product_id],
        feedback_id=fb.id,
        analysis_run_id=run.id,
    )

    # 4. Embedding từ feedback_text (PII boundary) — luôn kèm model + dim.
    vector = embed_one(fb.feedback_text)
    store_embedding(db, fb, vector)


def _process_chunk(
    db: Session,
    run: AnalysisRun,
    rows: list[Feedback],
    taxonomy_cache: dict[uuid.UUID, list[tuple[str, str]]],
    version_cache: dict[uuid.UUID, int],
) -> None:
    """One enrich call + one embedding-array call for a true batch chunk."""
    for fb in rows:
        if fb.feedback_text is None:
            result = sanitize(fb.raw_content)
            fb.feedback_text = result.sanitized_text
            fb.pii_detected = result.pii_detected
            fb.pii_entities = [entity.model_dump() for entity in result.entities]
        if fb.product_id not in taxonomy_cache:
            taxonomy_cache[fb.product_id] = _taxonomy_labels(db, fb.product_id)
        if fb.product_id not in version_cache:
            version_cache[fb.product_id] = (
                db.scalar(
                    select(Product.taxonomy_version).where(Product.id == fb.product_id)
                )
                or 1
            )
    labels = taxonomy_cache[rows[0].product_id]
    enriched = enrich_feedback_batch(
        [(fb.id, fb.feedback_text or "") for fb in rows],
        taxonomy_labels=labels,
        taxonomy_version=version_cache[rows[0].product_id],
        analysis_run_id=run.id,
    )
    vectors = embed_texts([fb.feedback_text or "" for fb in rows])
    if len(vectors) != len(rows):
        raise EmbeddingDimError("Embedding batch response count mismatch.")
    for fb, vector in zip(rows, vectors, strict=True):
        fb.ai_analysis = enriched[fb.id]
        store_embedding(db, fb, vector)


def run_analysis(run_id: uuid.UUID) -> None:
    from app.core.observability import telemetry

    with telemetry.operation("listen", run_id) as measurement:
        measurement["outcome"] = _run_analysis(run_id)


def _run_analysis(run_id: uuid.UUID) -> str:
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
            return "missing"

        attempted: set[uuid.UUID] = set()
        errors: list[str] = []
        processed_this_pass = 0
        taxonomy_cache: dict[uuid.UUID, list[tuple[str, str]]] = {}
        version_cache: dict[uuid.UUID, int] = {}

        try:
            while True:
                db.refresh(run)
                if run.cancel_requested_at is not None:
                    _release_unprocessed(db, run.id)
                    run.status = RunStatus.cancelled
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    return "cancelled"

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
                        _process_chunk(db, run, rows, taxonomy_cache, version_cache)
                    else:
                        _process_item(db, run, rows[0], taxonomy_cache, version_cache)
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
                        return "failed"
                    # Commit NGAY bookkeeping lỗi (unclaim + failed_count): vòng
                    # lặp mở đầu bằng db.refresh(run) — refresh sẽ DISCARD mọi
                    # mutation chưa commit của run (failed_count từng âm thầm
                    # mất khi chunk sau xử lý tiếp bình thường).
                    db.commit()
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
            return "failed"

    logger.info(
        "run %s hoàn tất: +%d item trong %.1fs",
        run_id,
        processed_this_pass,
        time.perf_counter() - started,
    )
    return "completed"


def _join_errors(errors: list[str]) -> str:
    summary = " | ".join(errors)
    return summary[:_ERROR_SUMMARY_MAX]


__all__ = ["PIPELINE_VERSION", "PROMPT_VERSION", "run_analysis"]

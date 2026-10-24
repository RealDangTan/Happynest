"""LISTEN v5: bounded per-item provider I/O, one persistence coordinator.

One sanitized feedback still produces one enrich and one embedding request.
Workers receive plain snapshots and capture only call metadata. A single DB
session commits each result, its logs and its progress increment atomically.
Cancellation/failure drains started requests before releasing unstarted claims.
A crash leaves unfinished claims resumable; completed items are never repaid.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from types import SimpleNamespace

from openai import APIError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs.analysis_workers import process_items
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.models.feedback import Feedback
from app.models.product import Product
from app.services import taxonomy_service, tracing
from app.services.embedder import embed_one, store_embedding
from app.services.enricher import PROMPT_VERSION, enrich_feedback
from app.services.llm_client import LLMStructureError
from app.services.presidio_service import sanitize

logger = logging.getLogger(__name__)
PIPELINE_VERSION = "v5"
_ITEM_ERRORS = (LLMStructureError, APIError)
_ERROR_SUMMARY_MAX = 2000
_active_runs: set[uuid.UUID] = set()
_active_lock = Lock()


@dataclass(frozen=True)
class ItemInput:
    id: uuid.UUID
    text: str
    pii_detected: bool
    pii_entities: list
    labels: list[tuple[str, str]]
    taxonomy_version: int


@dataclass
class ItemResult:
    values: dict = field(default_factory=dict)
    logs: list[dict] = field(default_factory=list)
    error: Exception | None = None


def _release_unprocessed(db: Session, run_id: uuid.UUID) -> None:
    db.execute(update(Feedback).where(
        Feedback.analysis_run_id == run_id, Feedback.ai_analysis.is_(None),
    ).values(analysis_run_id=None))


def _pending_items(db: Session, run_id: uuid.UUID) -> list[ItemInput]:
    # Do not fetch the 1536-dimensional vector or raw text for sanitized rows.
    rows = db.execute(select(
        Feedback.id, Feedback.product_id, Feedback.feedback_text,
        Feedback.pii_detected, Feedback.pii_entities,
    ).where(Feedback.analysis_run_id == run_id, Feedback.ai_analysis.is_(None))
        .order_by(Feedback.occurred_at, Feedback.id)).all()
    taxonomy, versions = {}, {}
    items = []
    for row in rows:
        if row.product_id not in taxonomy:
            taxonomy[row.product_id] = taxonomy_service.get_taxonomy_labels(db, row.product_id)
            versions[row.product_id] = db.scalar(select(Product.taxonomy_version)
                .where(Product.id == row.product_id)) or 1
        text, detected, entities = row.feedback_text, row.pii_detected, row.pii_entities
        if text is None:
            raw = db.scalar(select(Feedback.raw_content).where(Feedback.id == row.id))
            sanitized = sanitize(raw)
            text, detected = sanitized.sanitized_text, sanitized.pii_detected
            entities = [entry.model_dump() for entry in sanitized.entities]
        items.append(ItemInput(row.id, text, detected, entities,
            taxonomy[row.product_id], versions[row.product_id]))
    return items


def _compute_item(item: ItemInput, run_id: uuid.UUID) -> ItemResult:
    result = ItemResult()
    with tracing.capture_call_logs(analysis_run_id=run_id, feedback_id=item.id) as logs:
        result.logs = logs
        try:
            analysis = enrich_feedback(item.text, item.labels,
                taxonomy_version=item.taxonomy_version,
                feedback_id=item.id, analysis_run_id=run_id)
            embedding = SimpleNamespace()
            store_embedding(None, embedding, embed_one(item.text))
            result.values = dict(ai_analysis=analysis, feedback_text=item.text,
                pii_detected=item.pii_detected, pii_entities=item.pii_entities,
                **vars(embedding))
        except Exception as exc:  # coordinator distinguishes item errors from crashes
            result.error = exc
    return result


def run_analysis(run_id: uuid.UUID) -> None:
    from app.core.observability import telemetry

    # Resume/start races within this native process must not duplicate paid calls.
    with _active_lock:
        if run_id in _active_runs:
            logger.warning("run_analysis: run already active: %s", run_id)
            return
        _active_runs.add(run_id)
    try:
        with telemetry.operation("listen", run_id) as measurement:
            measurement["outcome"] = _run_analysis(run_id)
    finally:
        with _active_lock:
            _active_runs.discard(run_id)


def _run_analysis(run_id: uuid.UUID) -> str:
    started = time.perf_counter()
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            return "missing"
        if run.status in (RunStatus.completed, RunStatus.cancelled):
            return run.status.value
        total_count = run.total_count
        failed_count = run.failed_count
        halt = "cancelled" if run.cancel_requested_at is not None else None
        fatal = False
        errors: list[str] = []
        processed = 0
        try:
            items = [] if halt else _pending_items(db, run_id)
            # Release the connection before provider I/O; no ORM object is sent
            # to a worker and no DB transaction remains open during inference.
            db.expunge_all()
            db.rollback()

            def should_stop():
                nonlocal halt
                if halt:
                    return True
                # The UPDATE in save() also returns the current cancel flag.
                # This initial check catches cancellation during snapshot loading.
                if processed == 0 and failed_count == run.failed_count:
                    cancel = db.scalar(select(AnalysisRun.cancel_requested_at)
                        .where(AnalysisRun.id == run_id))
                    db.rollback()
                    if cancel is not None:
                        halt = "cancelled"
                return halt is not None

            def save(item: ItemInput, result: ItemResult):
                nonlocal failed_count, processed, halt, fatal
                for metadata in result.logs:
                    tracing.write_llm_call_log(db, **metadata)
                # Explicitly guard the original run claim and pending state.
                # Deleting/unclaiming an item must not resurrect or overwrite it.
                claim = (Feedback.id == item.id, Feedback.analysis_run_id == run_id,
                    Feedback.ai_analysis.is_(None))
                increments = {}
                if result.error is None:
                    changed = db.execute(update(Feedback).where(*claim)
                        .values(**result.values)).rowcount
                    if changed:
                        increments["processed_count"] = AnalysisRun.processed_count + 1
                elif isinstance(result.error, _ITEM_ERRORS):
                    changed = db.execute(update(Feedback).where(*claim)
                        .values(analysis_run_id=None)).rowcount
                    if changed:
                        increments["failed_count"] = AnalysisRun.failed_count + 1
                        failed_count += 1
                    errors.append(f"{item.id}: {type(result.error).__name__}: {result.error}"[:300])
                else:
                    fatal = True
                    halt = "failed"
                    errors.append(f"{item.id}: {type(result.error).__name__}"[:300])
                    logger.error("run %s item %s failed: %s", run_id, item.id,
                        type(result.error).__name__)
                if increments:
                    cancel = db.scalar(update(AnalysisRun).where(AnalysisRun.id == run_id)
                        .values(**increments).returning(AnalysisRun.cancel_requested_at))
                    if cancel is not None and halt != "failed":
                        halt = "cancelled"
                db.commit()
                if "processed_count" in increments:
                    processed += 1
                if failed_count * 2 > max(total_count, 1):
                    halt = "failed"

            process_items(items, lambda item: _compute_item(item, run_id), save,
                should_stop, max_workers=settings.ANALYSIS_WORKERS)
            status = halt or "completed"
            if halt and not fatal:
                _release_unprocessed(db, run_id)
            db.execute(update(AnalysisRun).where(AnalysisRun.id == run_id).values(
                status=RunStatus(status), completed_at=datetime.now(timezone.utc),
                error=_join_errors(errors) if errors else None))
            db.commit()
        except Exception as exc:
            db.rollback()
            db.execute(update(AnalysisRun).where(AnalysisRun.id == run_id).values(
                status=RunStatus.failed, completed_at=datetime.now(timezone.utc),
                error=f"{type(exc).__name__}: persistence/coordination failed"))
            db.commit()
            logger.exception("run %s crashed after %d items", run_id, processed)
            return "failed"
    logger.info("run %s: +%d items in %.1fs", run_id, processed, time.perf_counter() - started)
    return status


def _join_errors(errors: list[str]) -> str:
    return " | ".join(errors)[:_ERROR_SUMMARY_MAX]


__all__ = ["PIPELINE_VERSION", "PROMPT_VERSION", "run_analysis"]

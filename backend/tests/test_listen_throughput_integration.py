"""Real PG persistence/cancellation; every provider is replaced by safe fixtures."""

from datetime import datetime, timezone, timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs import analysis_runner
from app.models.analysis_run import AnalysisRun
from app.models.enums import LlmCallType, RunStatus
from app.models.feedback import Feedback
from app.models.llm_call_log import LlmCallLog
from app.services import embedder, llm_client, tracing
from app.services.llm_client import LLMStructureError

pytestmark = pytest.mark.integration

ENRICHMENT = {
    "topics": [], "topic_scores": [], "topic_confidence": 0., "uncategorized": True,
    "sentiment": "neutral", "emotions": ["neutral"], "emotion_scores": [],
    "intent": "other", "severity": "low", "safety_issue": False, "ai_issue": None,
    "confidence": .8, "rationale": "Synthetic fixture", "taxonomy_version": 1,
    "analysis_version": "enrich-v3",
}


@pytest.fixture
def batches(test_product, monkeypatch):
    created = []
    monkeypatch.setenv("ANALYSIS_WORKERS", "3")
    get_settings.cache_clear()
    monkeypatch.setattr(analysis_runner.taxonomy_service, "get_taxonomy_labels", lambda *a: [])
    monkeypatch.setattr(tracing, "trace_llm_call", lambda **kwargs: None)

    def create(n):
        with SessionLocal() as db:
            run = AnalysisRun(id=uuid4(), product_id=test_product.id,
                pipeline_version=analysis_runner.PIPELINE_VERSION, llm_model="synthetic",
                prompt_version="jev-v1", embedding_model="synthetic", total_count=n)
            db.add(run)
            db.flush()
            ids = []
            for i in range(n):
                fid = uuid4()
                ids.append(fid)
                db.add(Feedback(id=fid, product_id=test_product.id, analysis_run_id=run.id,
                    source="test-throughput", occurred_at=datetime.now(timezone.utc)+timedelta(seconds=i),
                    raw_content=f"synthetic safe {i}", feedback_text=f"synthetic safe {i}"))
            db.commit()
            created.append((run.id, ids))
            return run.id, ids

    yield create
    with SessionLocal() as db:
        for rid, ids in created:
            db.query(LlmCallLog).filter(LlmCallLog.analysis_run_id == rid).delete(synchronize_session=False)
            db.query(Feedback).filter(Feedback.id.in_(ids)).delete(synchronize_session=False)
            db.query(AnalysisRun).filter(AnalysisRun.id == rid).delete(synchronize_session=False)
        db.commit()
    get_settings.cache_clear()


def record_enrich(*, feedback_id, analysis_run_id, error=None):
    llm_client._record_attempt(name="synthetic", input_text_sanitized="safe synthetic",
        output_text="", schema_name="EnrichmentOut", call_type=LlmCallType.enrich,
        prompt_version="jev-v1", model="synthetic", latency_ms=50, usage=None,
        error=error, feedback_id=feedback_id, analysis_run_id=analysis_run_id,
        session_factory=SessionLocal)


def fake_embed(text):
    embedder._log_call(latency_ms=70, prompt_tokens=5)
    return [1.] + [0.] * 1535


def test_parallel_items_commit_logs_progress_and_resume_without_repaying(batches, monkeypatch):
    rid, ids = batches(6)
    barrier = Barrier(3)
    calls = []

    def enrich(text, labels, **kwargs):
        calls.append(kwargs["feedback_id"])
        barrier.wait(timeout=10)
        record_enrich(feedback_id=kwargs["feedback_id"], analysis_run_id=kwargs["analysis_run_id"])
        return dict(ENRICHMENT)

    monkeypatch.setattr(analysis_runner, "enrich_feedback", enrich)
    monkeypatch.setattr(analysis_runner, "embed_one", fake_embed)
    analysis_runner.run_analysis(rid)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert (run.status, run.processed_count, run.failed_count) == (RunStatus.completed, 6, 0)
        rows = db.scalars(select(Feedback).where(Feedback.id.in_(ids))).all()
        assert all(row.ai_analysis == ENRICHMENT and row.embedding is not None for row in rows)
        logs = db.scalars(select(LlmCallLog).where(LlmCallLog.analysis_run_id == rid)).all()
        assert len(logs) == 12
        assert {log.feedback_id for log in logs} == set(ids)
        assert all(sum(log.feedback_id == fid for log in logs) == 2 for fid in ids)
    analysis_runner.run_analysis(rid)
    assert len(calls) == 6 and set(calls) == set(ids)


def test_cancel_drains_only_inflight_and_releases_unstarted_claims(batches, monkeypatch):
    rid, ids = batches(8)
    barrier, cancelled = Barrier(3), Event()

    def enrich(text, labels, **kwargs):
        barrier.wait(timeout=10)
        if text.endswith(" 0"):
            with SessionLocal() as db:
                db.execute(update(AnalysisRun).where(AnalysisRun.id == rid)
                    .values(cancel_requested_at=datetime.now(timezone.utc)))
                db.commit()
            cancelled.set()
        else:
            assert cancelled.wait(timeout=10)
        record_enrich(feedback_id=kwargs["feedback_id"], analysis_run_id=rid)
        return dict(ENRICHMENT)

    monkeypatch.setattr(analysis_runner, "enrich_feedback", enrich)
    monkeypatch.setattr(analysis_runner, "embed_one", fake_embed)
    analysis_runner.run_analysis(rid)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert (run.status, run.processed_count) == (RunStatus.cancelled, 3)
        rows = db.scalars(select(Feedback).where(Feedback.id.in_(ids))).all()
        assert sum(row.ai_analysis is not None for row in rows) == 3
        assert sum(row.analysis_run_id is None for row in rows) == 5
        assert len(db.scalars(select(LlmCallLog).where(LlmCallLog.analysis_run_id == rid)).all()) == 6


def test_failure_limit_preserves_error_logs_and_unclaims_remaining(batches, monkeypatch):
    rid, ids = batches(8)

    def enrich(text, labels, **kwargs):
        record_enrich(feedback_id=kwargs["feedback_id"], analysis_run_id=rid, error="synthetic failure")
        raise LLMStructureError("synthetic failure")

    monkeypatch.setattr(analysis_runner, "enrich_feedback", enrich)
    monkeypatch.setattr(analysis_runner, "embed_one", lambda text: pytest.fail("failed enrich must not embed"))
    analysis_runner.run_analysis(rid)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert run.status == RunStatus.failed and run.failed_count > 4
        assert run.processed_count == 0
        rows = db.scalars(select(Feedback).where(Feedback.id.in_(ids))).all()
        assert all(row.analysis_run_id is None and row.ai_analysis is None for row in rows)
        logs = db.scalars(select(LlmCallLog).where(LlmCallLog.analysis_run_id == rid)).all()
        assert len(logs) == run.failed_count and all(log.error for log in logs)


def test_embedding_crash_keeps_claims_resumable_and_does_not_repeat_completed_items(batches, monkeypatch):
    rid, ids = batches(6)
    calls = []
    barrier = Barrier(3)

    def enrich(text, labels, **kwargs):
        calls.append(kwargs["feedback_id"])
        record_enrich(feedback_id=kwargs["feedback_id"], analysis_run_id=rid)
        return dict(ENRICHMENT)

    def crash_embed(text):
        barrier.wait(timeout=10)
        if text.endswith(" 0"):
            embedder._log_call(latency_ms=70, error="synthetic crash")
            raise RuntimeError("synthetic crash")
        Event().wait(.3)  # let the crashing result stop further submissions
        return fake_embed(text)

    monkeypatch.setattr(analysis_runner, "enrich_feedback", enrich)
    monkeypatch.setattr(analysis_runner, "embed_one", crash_embed)
    analysis_runner.run_analysis(rid)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert run.status == RunStatus.failed and run.processed_count == 2
        completed_ids = set(db.scalars(select(Feedback.id).where(
            Feedback.analysis_run_id == rid, Feedback.ai_analysis.is_not(None))).all())
        assert len(completed_ids) == 2
        assert len(db.scalars(select(LlmCallLog).where(LlmCallLog.analysis_run_id == rid)).all()) == 6
    monkeypatch.setattr(analysis_runner, "embed_one", fake_embed)
    analysis_runner.run_analysis(rid)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert run.status == RunStatus.completed and run.processed_count == 6
    assert all(calls.count(fid) == 1 for fid in completed_ids)
    assert set(calls) == set(ids)

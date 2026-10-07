"""Integration plan 32 — runner v3 idempotent/resumable với enricher mock.

Thay thế suite `test_classifier_idempotency` cũ (classifier bị strip):
- run batch hoàn tất, `ai_analysis` khớp preset enrich v3 trên từng item;
- chunk fail (LLMStructureError) → unclaim + failed_count; gọi lại `run_analysis`
  RESUME cùng run, không xử lý lại item đã xong.
Self-seeding: import + feedback riêng (`source="test-enrich"`), dọn trong teardown.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.jobs import analysis_runner
from app.models.analysis_run import AnalysisRun
from app.models.enums import ImportStatus, RunStatus
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.services import taxonomy_service

pytestmark = pytest.mark.integration

_ENRICHMENT = {
    "topics": ["nhãn-test"],
    "topic_scores": [{"id": "nhãn-test", "probability": 0.91}],
    "topic_confidence": 0.91,
    "uncategorized": False,
    "sentiment": "neutral",
    "emotions": ["neutral"],
    "emotion_scores": [],
    "intent": "question",
    "severity": "low",
    "safety_issue": False,
    "ai_issue": None,
    "confidence": 0.85,
    "rationale": "Preset mock enrich v3.",
    "taxonomy_version": 1,
    "analysis_version": "enrich-v3",
}


@pytest.fixture()
def enrich_env(test_product):
    created = {"feedback_ids": [], "import_id": None, "run_id": None}

    def _cleanup():
        with SessionLocal() as db:
            db.query(Feedback).filter(Feedback.source == "test-enrich").delete(
                synchronize_session=False
            )
            if created["import_id"]:
                db.query(AnalysisRun).filter(
                    AnalysisRun.import_id == created["import_id"]
                ).delete(synchronize_session=False)
                imp = db.get(Import, created["import_id"])
                if imp:
                    db.delete(imp)
            db.commit()

    _cleanup()
    yield created
    _cleanup()


def _seed_rows(product_id, import_id, run_id, n):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        for i in range(n):
            fb = Feedback(
                product_id=product_id,
                import_id=import_id,
                analysis_run_id=run_id,
                source="test-enrich",
                source_record_id=f"row-{i}",
                occurred_at=now,
                raw_content=f"noi dung gia {i} (khong PII)",
                feedback_text=f"noi dung gia {i}",
            )
            db.add(fb)
            db.commit()
            db.refresh(fb)
            yield fb.id


def test_batch_enrich_completes_and_shape_matches(test_product, enrich_env, monkeypatch) -> None:
    with SessionLocal() as db:
        imp = Import(
            product_id=test_product.id,
            source_type="csv",
            original_filename="enrich-idem.csv",
            status=ImportStatus.imported,
        )
        db.add(imp)
        db.commit()
        db.refresh(imp)
        run = AnalysisRun(
            pipeline_version=analysis_runner.PIPELINE_VERSION,
            llm_model="mock/enricher",
            prompt_version=analysis_runner.PROMPT_VERSION,
            embedding_model="mock-embed",
            import_id=imp.id,
            mode="batch",
            chunk_size=3,
            total_count=7,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        enrich_env["import_id"], enrich_env["run_id"] = imp.id, run.id
        ids = list(_seed_rows(test_product.id, imp.id, run.id, 7))
    monkeypatch.setattr(
        taxonomy_service, "get_taxonomy_labels", lambda *a, **k: [("nhãn-test", "Nhãn test")]
    )

    calls: list[int] = []

    def fake_enrich(items, **kwargs):
        calls.append(len(items))
        assert kwargs.get("taxonomy_version") is not None
        return {fid: dict(_ENRICHMENT) for fid, _ in items}

    monkeypatch.setattr(analysis_runner, "enrich_feedback_batch", fake_enrich)
    monkeypatch.setattr(
        analysis_runner, "embed_texts", lambda texts: [[0.0] * 1536 for _ in texts]
    )

    analysis_runner.run_analysis(enrich_env["run_id"])

    assert calls == [3, 3, 1]  # chunk_size=3, 7 items — batch đúng Gregory pattern
    with SessionLocal() as db:
        finished = db.get(AnalysisRun, enrich_env["run_id"])
        assert finished.status == RunStatus.completed
        assert finished.processed_count == 7
        rows = db.scalars(
            select(Feedback).where(Feedback.source == "test-enrich")
        ).all()
        assert len(rows) == 7
        for row in rows:
            assert row.ai_analysis == _ENRICHMENT
            assert row.embedding is not None or row.has_embedding is False


def test_chunk_fail_unclaims_then_resume_completes(test_product, enrich_env, monkeypatch) -> None:
    with SessionLocal() as db:
        imp = Import(
            product_id=test_product.id,
            source_type="csv",
            original_filename="enrich-resume.csv",
            status=ImportStatus.imported,
        )
        db.add(imp)
        db.commit()
        db.refresh(imp)
        run = AnalysisRun(
            pipeline_version=analysis_runner.PIPELINE_VERSION,
            llm_model="mock/enricher",
            prompt_version=analysis_runner.PROMPT_VERSION,
            embedding_model="mock-embed",
            import_id=imp.id,
            mode="batch",
            chunk_size=2,
            total_count=4,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        enrich_env["import_id"], enrich_env["run_id"] = imp.id, run.id
        list(_seed_rows(test_product.id, imp.id, run.id, 4))
    monkeypatch.setattr(taxonomy_service, "get_taxonomy_labels", lambda *a, **k: [])
    monkeypatch.setattr(
        analysis_runner, "embed_texts", lambda texts: [[0.0] * 1536 for _ in texts]
    )

    from app.services.llm_client import LLMStructureError

    state = {"calls": 0}

    def flaky_enrich(items, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise LLMStructureError("mock provider junk")
        return {fid: dict(_ENRICHMENT) for fid, _ in items}

    monkeypatch.setattr(analysis_runner, "enrich_feedback_batch", flaky_enrich)
    # mode="selected" đi đường item đơn — phải mock NHAU ĐẦY ĐỦ (quy tắc:
    # test tự động KHÔNG BAO GIỜ gọi LLM thật).
    monkeypatch.setattr(
        analysis_runner,
        "enrich_feedback",
        lambda text, labels, **kwargs: dict(_ENRICHMENT),
    )

    # Lượt 1: chunk đầu fail → unclaim + failed_count durable, run completed
    # với phần còn lại (2/4 fail < 50% → không dừng sớm).
    analysis_runner.run_analysis(enrich_env["run_id"])
    with SessionLocal() as db:
        run = db.get(AnalysisRun, enrich_env["run_id"])
        assert run.status == RunStatus.completed
        assert run.failed_count == 2  # plan 32 fix: KHÔNG còn bị refresh discard
        assert run.processed_count == 2
        done = db.scalars(
            select(Feedback).where(
                Feedback.source == "test-enrich", Feedback.ai_analysis.is_not(None)
            )
        ).all()
        assert len(done) == 2
        released = db.scalars(
            select(Feedback).where(
                Feedback.source == "test-enrich",
                Feedback.analysis_run_id.is_(None),
                Feedback.ai_analysis.is_(None),
            )
        ).all()
        assert len(released) == 2
        released_ids = [r.id for r in released]

    # Lượt 2: item released được nhặt lại bởi run MỚI (claim mới) — enrich theo
    # taxonomy hiện tại, không đụng item đã xong.
    with SessionLocal() as db:
        run2 = AnalysisRun(
            pipeline_version=analysis_runner.PIPELINE_VERSION,
            llm_model="mock/enricher",
            prompt_version=analysis_runner.PROMPT_VERSION,
            embedding_model="mock-embed",
            import_id=enrich_env["import_id"],
            mode="selected",
            chunk_size=1,
            total_count=2,
        )
        db.add(run2)
        db.commit()
        db.refresh(run2)
        run2_id = run2.id
        for fid in released_ids:
            row = db.get(Feedback, fid)
            row.analysis_run_id = run2_id
        db.commit()

    analysis_runner.run_analysis(run2_id)
    with SessionLocal() as db:
        run2 = db.get(AnalysisRun, run2_id)
        assert run2.status == RunStatus.completed
        assert run2.processed_count == 2
        rows = db.scalars(
            select(Feedback)
            .where(Feedback.source == "test-enrich")
            .order_by(Feedback.source_record_id)
        ).all()
        assert all(r.ai_analysis == _ENRICHMENT for r in rows)

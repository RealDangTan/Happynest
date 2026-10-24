"""Phase 28 integration contracts. All provider calls are mocked."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.db.session import SessionLocal
from app.jobs import analysis_runner
from app.models.analysis_run import AnalysisRun
from app.models.enums import ImportStatus, RunStatus
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.services import import_service
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _auth(client) -> dict[str, str]:
    response = client.post(
        "/api/auth/token",
        data={
            "username": SEED_EMAILS["primary"],
            "password": TEST_PASSWORDS["primary"],
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_upload_profiles_without_calling_mapper_and_cancel_deletes_raw(
    client, test_product, monkeypatch
):
    calls = 0

    def forbidden_mapper(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("mapper must not run during upload")

    monkeypatch.setattr(import_service, "build_mapping_proposal", forbidden_mapper)
    response = client.post(
        "/api/imports",
        files={
            "file": (
                "budget.csv",
                b"message,email\nGreat app,user@example.com\n",
                "text/csv",
            )
        },
        data={"product_id": str(test_product.id)},
        headers=_auth(client),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "profile_ready"
    assert calls == 0
    raw_path = Path(body["storage_path"])
    assert raw_path.exists()

    preview = client.get(
        f"/api/imports/{body['id']}/preview", headers=_auth(client)
    )
    assert preview.status_code == 200
    assert "user@example.com" not in preview.text

    cancelled = client.post(
        f"/api/imports/{body['id']}/cancel", headers=_auth(client)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert not raw_path.exists()
    with SessionLocal() as db:
        db.query(Import).filter(Import.id == uuid.UUID(body["id"])).delete()
        db.commit()


def test_singular_23_feedback_uses_one_call_per_item(test_product, monkeypatch):
    """v4 singular (owner 2026-10-22): 23 item = 23 enrich call + 23 embed call."""
    classify_calls: list[str] = []
    embedding_calls: list[str] = []
    with SessionLocal() as db:
        import_row = Import(
            product_id=test_product.id,
            source_type="csv",
            status=ImportStatus.imported,
            source_row_count=23,
            row_count=23,
        )
        run = AnalysisRun(
            pipeline_version="v2",
            llm_model="mock",
            prompt_version="v2",
            embedding_model="mock",
            import_id=None,
            mode="batch",
            chunk_size=10,
            total_count=23,
        )
        db.add_all([import_row, run])
        db.flush()
        run.import_id = import_row.id
        for index in range(23):
            db.add(
                Feedback(
                    product_id=test_product.id,
                    import_id=import_row.id,
                    analysis_run_id=run.id,
                    source="test",
                    occurred_at=datetime(2026, 8, 30, 0, index, tzinfo=UTC),
                    raw_content=f"safe {index}",
                    feedback_text=f"safe {index}",
                    data={},
                    source_meta={},
                )
            )
        db.commit()
        run_id, import_id = run.id, import_row.id

    enrichment = {
        "topics": ["quality"],
        "topic_scores": [{"id": "quality", "probability": 0.9}],
        "topic_confidence": 0.9,
        "uncategorized": False,
        "sentiment": "neutral",
        "emotions": ["neutral"],
        "emotion_scores": [],
        "intent": "other",
        "severity": "low",
        "safety_issue": False,
        "ai_issue": None,
        "confidence": 0.9,
        "rationale": "Mocked.",
        "taxonomy_version": 1,
        "analysis_version": "enrich-v3",
    }

    def fake_enrich(text, labels, *, feedback_id=None, analysis_run_id=None, **kwargs):
        classify_calls.append(text)
        return dict(enrichment)

    def fake_embed(text):
        embedding_calls.append(text)
        return [0.0] * 1536

    monkeypatch.setattr(analysis_runner, "enrich_feedback", fake_enrich)
    monkeypatch.setattr(analysis_runner, "embed_one", fake_embed)
    monkeypatch.setattr(
        analysis_runner.taxonomy_service, "get_taxonomy_labels", lambda *a: []
    )

    analysis_runner.run_analysis(run_id)

    assert len(classify_calls) == 23
    assert len(embedding_calls) == 23
    with SessionLocal() as db:
        finished = db.get(AnalysisRun, run_id)
        assert finished.status == RunStatus.completed
        assert finished.processed_count == 23
        db.query(Feedback).filter(Feedback.analysis_run_id == run_id).delete(
            synchronize_session=False
        )
        db.delete(finished)
        db.query(Import).filter(Import.id == import_id).delete()
        db.commit()

"""Phase 28 integration contracts. All provider calls are mocked."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.db.session import SessionLocal
from app.jobs import analysis_runner
from app.models.analysis_run import AnalysisRun
from app.models.enums import ImportStatus, RunStatus, UserRole
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.schemas.taxonomy import Classification
from app.services import import_service
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _auth(client) -> dict[str, str]:
    response = client.post(
        "/api/auth/token",
        data={
            "username": SEED_EMAILS[UserRole.pm],
            "password": TEST_PASSWORDS[UserRole.pm],
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


def test_batch_23_feedback_uses_three_classify_and_embedding_calls(
    test_product, monkeypatch
):
    classify_calls: list[int] = []
    embedding_calls: list[int] = []
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

    classification = Classification(
        categories=["quality"],
        ai_issue=None,
        sentiment="neutral",
        severity="low",
        safety_issue=False,
        confidence=0.9,
        rationale="Mocked.",
    )

    def fake_classify(items, **kwargs):
        classify_calls.append(len(items))
        return {item_id: classification for item_id, _ in items}

    def fake_embed(texts):
        embedding_calls.append(len(texts))
        return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(analysis_runner, "classify_feedback_batch", fake_classify)
    monkeypatch.setattr(analysis_runner, "embed_texts", fake_embed)
    monkeypatch.setattr(analysis_runner.taxonomy_service, "get_taxonomy_names", lambda *a: [])
    monkeypatch.setattr(analysis_runner.taxonomy_service, "accumulate_emerging", lambda *a, **k: None)

    analysis_runner.run_analysis(run_id)

    assert classify_calls == [10, 10, 3]
    assert embedding_calls == [10, 10, 3]
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

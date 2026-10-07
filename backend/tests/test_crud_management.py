"""Integration test — CRUD quản lý (plan crud-management-screens 2026-09-16).

PATCH/DELETE feedback (đơn + bulk), DELETE import batch, DELETE product
cascade, PATCH/DELETE insight. Destructive ops guard pm-only (operations → 403).

Chạy: `uv run pytest -m integration tests/test_crud_management.py -v`
Suite tự seed product RIÊNG (tên cố định, idempotent) + teardown xoá sạch mọi
row liên quan theo convention conftest (không đụng data demo của DB chung).
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.action import Action
from app.models.analysis_run import AnalysisRun
from app.models.enums import BusinessFunction, ImportStatus, LlmCallType, RunStatus, UserRole
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.insight import Insight
from app.models.llm_call_log import LlmCallLog
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_PRODUCT_NAME = "crud-mgmt-test-product"
_SRC = "test-crud-mgmt"


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def crud_product():
    """Product riêng của suite; teardown dọn mọi bảng con trước khi xoá product."""
    with SessionLocal() as db:
        product = db.query(Product).filter(Product.name == _PRODUCT_NAME).first()
        if product is None:
            product = Product(name=_PRODUCT_NAME, description="CRUD test suite")
            db.add(product)
            db.commit()
            db.refresh(product)
        pid = product.id
    yield pid
    with SessionLocal() as db:
        run_ids = (
            select(AnalysisRun.id)
            .where(
                AnalysisRun.import_id.in_(
                    select(Import.id).where(Import.product_id == pid)
                )
            )
            .scalar_subquery()
        )
        db.query(LlmCallLog).filter(
            LlmCallLog.analysis_run_id.in_(run_ids)
        ).delete(synchronize_session=False)
        db.query(Evidence).filter(Evidence.product_id == pid).delete(
            synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.product_id == pid).delete(
            synchronize_session=False
        )
        db.query(Insight).filter(Insight.product_id == pid).delete(
            synchronize_session=False
        )
        db.query(Taxonomy).filter(Taxonomy.product_id == pid).delete(
            synchronize_session=False
        )
        db.query(AnalysisRun).filter(
            AnalysisRun.import_id.in_(select(Import.id).where(Import.product_id == pid))
        ).delete(synchronize_session=False)
        db.query(Import).filter(Import.product_id == pid).delete(
            synchronize_session=False
        )
        db.query(Product).filter(Product.id == pid).delete(synchronize_session=False)
        db.commit()


def _seed_feedback(product_id: uuid.UUID, **overrides) -> uuid.UUID:
    with SessionLocal() as db:
        fb = Feedback(
            product_id=product_id,
            source=_SRC,
            source_record_id=f"crud-{uuid.uuid4().hex[:8]}",
            occurred_at=datetime.now(timezone.utc),
            raw_content="noi dung tho (khong PII)",
            feedback_text="noi dung tho",
            ai_analysis={"severity": "low", "sentiment": "neutral", "topics": ["t1"]},
            **overrides,
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return fb.id


# ------------------------------------------------------------- Phase A: feedback


def test_patch_feedback_resanitizes_and_clears_embedding(client, crud_product) -> None:
    auth = _login(client)
    fb_id = _seed_feedback(crud_product)
    with SessionLocal() as db:
        fb = db.get(Feedback, fb_id)
        from app.services.embedder import store_embedding

        store_embedding(db, fb, [0.1] * 1536)

    resp = client.patch(
        f"/api/feedbacks/{fb_id}",
        headers=auth,
        json={"feedback_text": "liên hệ tôi qua alice@example.com nhé, app crash liên tục"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "alice@example.com" not in body["feedback_text"], body
    assert body["pii_detected"] is True
    assert body["has_embedding"] is False

    with SessionLocal() as db:
        row = db.get(Feedback, fb_id)
        assert row.embedding is None
        assert row.feedback_text is not None and "alice@example.com" not in row.feedback_text


def test_patch_feedback_merges_labels_and_metadata(client, crud_product) -> None:
    auth = _login(client)
    fb_id = _seed_feedback(crud_product)

    resp = client.patch(
        f"/api/feedbacks/{fb_id}",
        headers=auth,
        json={
            "source": "email",
            "ai_analysis": {"severity": "high", "topics": ["t2"]},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "email"
    # Partial merge: giữ sentiment cũ, ghi đè severity/topics
    assert body["ai_analysis"]["sentiment"] == "neutral"
    assert body["ai_analysis"]["severity"] == "high"
    assert body["ai_analysis"]["topics"] == ["t2"]


def test_patch_feedback_operations_forbidden(client, crud_product) -> None:
    ops = _login(client, UserRole.operations)
    fb_id = _seed_feedback(crud_product)
    resp = client.patch(
        f"/api/feedbacks/{fb_id}", headers=ops, json={"source": "email"}
    )
    assert resp.status_code == 403, resp.text


def test_delete_feedback_single(client, crud_product) -> None:
    auth = _login(client)
    fb_id = _seed_feedback(crud_product)

    resp = client.delete(f"/api/feedbacks/{fb_id}", headers=auth)
    assert resp.status_code == 204, resp.text
    assert client.get(f"/api/feedbacks/{fb_id}", headers=auth).status_code == 404


def test_bulk_delete_feedback(client, crud_product) -> None:
    auth = _login(client)
    ids = [_seed_feedback(crud_product) for _ in range(3)]

    resp = client.post(
        "/api/feedbacks/bulk-delete",
        headers=auth,
        json={"ids": [str(ids[0]), str(ids[1]), str(uuid.uuid4())]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted"] == 2

    with SessionLocal() as db:
        left = db.scalars(
            select(Feedback.id).where(Feedback.id.in_(ids))
        ).all()
        assert left == [ids[2]]


def test_feedback_destructive_404(client, crud_product) -> None:
    auth = _login(client)
    missing = uuid.uuid4()
    assert client.delete(f"/api/feedbacks/{missing}", headers=auth).status_code == 404
    assert (
        client.patch(
            f"/api/feedbacks/{missing}", headers=auth, json={"source": "x"}
        ).status_code
        == 404
    )


# ------------------------------------------------------------- Phase B: import


def _seed_import(product_id: uuid.UUID, status: ImportStatus = ImportStatus.imported) -> Import:
    with SessionLocal() as db:
        row = Import(
            product_id=product_id,
            source_type="csv_legacy",
            status=status,
            original_filename="crud-test.csv",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


def test_delete_import_cascades(client, crud_product) -> None:
    auth = _login(client)
    imp = _seed_import(crud_product)
    with SessionLocal() as db:
        fb = Feedback(
            product_id=crud_product,
            import_id=imp.id,
            source=_SRC,
            occurred_at=datetime.now(timezone.utc),
            raw_content="r",
            feedback_text="f",
        )
        run = AnalysisRun(
            pipeline_version="test",
            llm_model="m",
            prompt_version="t1",
            embedding_model="e",
            import_id=imp.id,
            status=RunStatus.completed,
        )
        db.add(fb)
        db.add(run)
        db.flush()
        ev = Evidence(
            run_id=run.id,
            product_id=crud_product,
            type="test",
            statement="stmt",
            payload={},
            source_tool="test",
        )
        log = LlmCallLog(
            analysis_run_id=run.id,
            call_type=list(LlmCallType)[0],
            prompt_version="t1",
            model="m",
            latency_ms=1,
        )
        db.add(ev)
        db.add(log)
        db.commit()
        run_id, fb_id = run.id, fb.id

    resp = client.delete(f"/api/imports/{imp.id}", headers=auth)
    assert resp.status_code == 204, resp.text

    with SessionLocal() as db:
        assert db.get(Feedback, fb_id) is None
        assert db.get(AnalysisRun, run_id) is None
        assert db.get(Import, imp.id) is None
        assert db.query(Evidence).filter(Evidence.run_id == run_id).count() == 0
        assert (
            db.query(LlmCallLog)
            .filter(LlmCallLog.analysis_run_id == run_id)
            .count()
            == 0
        )


def test_delete_import_busy_409(client, crud_product) -> None:
    auth = _login(client)
    imp = _seed_import(crud_product, status=ImportStatus.mapping_generating)
    resp = client.delete(f"/api/imports/{imp.id}", headers=auth)
    assert resp.status_code == 409, resp.text


# ------------------------------------------------------------- Phase B: insight


def _seed_insight(product_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    with SessionLocal() as db:
        insight = Insight(
            product_id=product_id,
            title="Hallucinated title",
            finding="finding gốc",
            finding_confidence=0.5,
            affected_context={},
            impact=[],
            limitations=[],
            evidence=[],
        )
        db.add(insight)
        db.flush()
        action = Action(
            insight_id=insight.id,
            function=list(BusinessFunction)[0],
            recommendation="rec",
            rationale="why",
            impact=1,
            effort=1,
            urgency=1,
            confidence=0.5,
            priority_score=1.0,
        )
        db.add(action)
        db.commit()
        return insight.id, action.id


def test_patch_insight_edits_and_logs_review(client, crud_product) -> None:
    auth = _login(client)
    ins_id, _action_id = _seed_insight(crud_product)

    resp = client.patch(
        f"/api/insights/{ins_id}",
        headers=auth,
        json={"title": "Title đã sửa", "finding": "finding đã sửa"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Title đã sửa"
    assert body["finding"] == "finding đã sửa"
    assert body["status"] == "edited"

    from app.models.insight_review import InsightReview

    with SessionLocal() as db:
        reviews = (
            db.query(InsightReview).filter(InsightReview.insight_id == ins_id).all()
        )
        assert len(reviews) == 1
        assert reviews[0].edited_value is not None


def test_delete_insight_cascades_actions(client, crud_product) -> None:
    auth = _login(client)
    ins_id, action_id = _seed_insight(crud_product)

    resp = client.delete(f"/api/insights/{ins_id}", headers=auth)
    assert resp.status_code == 204, resp.text

    with SessionLocal() as db:
        assert db.get(Insight, ins_id) is None
        assert db.get(Action, action_id) is None


# ------------------------------------------------------------- Phase B: product


def test_delete_product_cascades_everything(client, crud_product) -> None:
    auth = _login(client)
    imp = _seed_import(crud_product)
    ins_id, _action_id = _seed_insight(crud_product)
    _seed_feedback(crud_product, import_id=imp.id)
    with SessionLocal() as db:
        db.add(Taxonomy(product_id=crud_product, name="topic-crud"))
        db.commit()

    resp = client.delete(f"/api/products/{crud_product}", headers=auth)
    assert resp.status_code == 200, resp.text
    counts = resp.json()["deleted_counts"]
    assert counts["feedbacks"] >= 1
    assert counts["insights"] >= 1
    assert counts["imports"] >= 1

    with SessionLocal() as db:
        assert db.get(Product, crud_product) is None
        assert db.get(Insight, ins_id) is None
        assert (
            db.query(Feedback).filter(Feedback.product_id == crud_product).count() == 0
        )
        assert (
            db.query(Import).filter(Import.product_id == crud_product).count() == 0
        )
        assert (
            db.query(Taxonomy).filter(Taxonomy.product_id == crud_product).count() == 0
        )


def test_product_destructive_pm_only(client, crud_product) -> None:
    ops = _login(client, UserRole.operations)
    resp = client.delete(f"/api/products/{crud_product}", headers=ops)
    assert resp.status_code == 403, resp.text

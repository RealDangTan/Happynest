"""Plan 34 — GPT topic recommendation + apply (human gate) + re-enrich loop.

⚠️ Marker `integration` — DB thật; KHÔNG LLM thật (recommend_topics mock ở tầng
service). Pool query test bằng seed `ai_analysis` shape v3 (uncategorized /
low-confidence / categorized).
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from app.schemas.taxonomy import (
    ProposedTopic,
    TaxonomyProposalOut,
    TopicRecommendation,
    TopicRecommendationOut,
)
from app.services import analysis_service, taxonomy_service
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def rec_env(test_product):
    def _clean():
        with SessionLocal() as db:
            db.query(Taxonomy).filter(
                Taxonomy.product_id == test_product.id
            ).delete(synchronize_session=False)
            db.query(Feedback).filter(
                Feedback.source == "test-recommend"
            ).delete(synchronize_session=False)
            db.commit()

    _clean()
    yield test_product
    _clean()


def _seed_feedback(product_id: uuid.UUID, ref: str, analysis: dict | None) -> uuid.UUID:
    with SessionLocal() as db:
        fb = Feedback(
            product_id=product_id,
            source="test-recommend",
            source_record_id=ref,
            occurred_at=datetime.now(UTC),
            raw_content=f"noi dung gia {ref} (khong PII)",
            feedback_text=f"noi dung gia {ref}",
            ai_analysis=analysis,
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return fb.id


def test_pool_only_uncategorized_or_low_confidence(rec_env) -> None:
    _seed_feedback(rec_env.id, "pool-uncat", {
        "topics": [], "uncategorized": True, "topic_confidence": None,
        "sentiment": "negative", "emotions": ["frustration"], "intent": "complaint",
        "severity": "medium", "safety_issue": False, "ai_issue": None,
        "confidence": 0.7, "rationale": "r", "taxonomy_version": 1, "analysis_version": "enrich-v3",
    })
    _seed_feedback(rec_env.id, "pool-low", {
        "topics": ["payment.payment_failure"], "uncategorized": False,
        "topic_confidence": 0.35, "topic_scores": [{"id": "payment.payment_failure", "probability": 0.35}],
        "sentiment": "negative", "emotions": ["frustration"], "intent": "bug_report",
        "severity": "high", "safety_issue": False, "ai_issue": None,
        "confidence": 0.5, "rationale": "r", "taxonomy_version": 1, "analysis_version": "enrich-v3",
    })
    _seed_feedback(rec_env.id, "ok-high", {
        "topics": ["payment.payment_failure"], "uncategorized": False,
        "topic_confidence": 0.94, "topic_scores": [{"id": "payment.payment_failure", "probability": 0.94}],
        "sentiment": "negative", "emotions": ["frustration"], "intent": "bug_report",
        "severity": "high", "safety_issue": False, "ai_issue": None,
        "confidence": 0.9, "rationale": "r", "taxonomy_version": 1, "analysis_version": "enrich-v3",
    })
    _seed_feedback(rec_env.id, "ok-null-analysis", None)

    with SessionLocal() as db:
        pool = taxonomy_service.find_unclassified_pool(db, rec_env.id)
        refs = sorted(r.source_record_id for r in pool)
    assert refs == ["pool-low", "pool-uncat"]


def test_recommend_stateless_and_apply_creates_nodes(rec_env, monkeypatch) -> None:
    with SessionLocal() as db:
        product = db.get(Product, rec_env.id)
        monkeypatch.setattr(
            taxonomy_service,
            "chat_structured",
            lambda *a, **k: TopicRecommendationOut(recommendations=[
                TopicRecommendation(
                    name="Lỗi hiển thị font", parent=None, evidence_count=2,
                    examples=["font chu loi o dashboard", "chu bi hoa thanh o ban iOS"],
                ),
            ]),
        )
        result, pool_count = taxonomy_service.recommend_topics(db, product)
    assert pool_count == 0  # pool rỗng → không gọi LLM (mock cũng không bị dùng)
    assert result.recommendations == []

    # Seed 2 uncategorized rồi recommend lại — mock trả 1 đề xuất
    _seed_feedback(rec_env.id, "rec-1", {"topics": [], "uncategorized": True})
    _seed_feedback(rec_env.id, "rec-2", {"topics": [], "uncategorized": True})
    with SessionLocal() as db:
        product = db.get(Product, rec_env.id)
        result, pool_count = taxonomy_service.recommend_topics(db, product)
    assert pool_count == 2
    assert result.recommendations[0].name == "Lỗi hiển thị font"

    # Apply qua đường dùng chung apply_proposal → idempotent lần 2
    proposal = TaxonomyProposalOut(topics=[ProposedTopic(name="Lỗi hiển thị font")])
    first = taxonomy_service.apply_proposal(SessionLocal(), rec_env, proposal)
    assert len(first["created"]) == 1
    second = taxonomy_service.apply_proposal(SessionLocal(), rec_env, proposal)
    assert second["created"] == [] and second["skipped"] == 1


def test_recommend_routes_and_re_enrich(client, rec_env, monkeypatch) -> None:
    auth = _login(client)
    with SessionLocal() as db:
        db.add(Taxonomy(product_id=rec_env.id, name="Search", slug="search",
                        kind="canonical", status="active"))
        db.commit()

    _seed_feedback(rec_env.id, "rr-1", {"topics": [], "uncategorized": True})
    _seed_feedback(rec_env.id, "rr-2", {"topics": [], "uncategorized": True})

    def _fake_recommend(db, product, *, pool_limit=100):
        return TopicRecommendationOut(recommendations=[
            TopicRecommendation(name="Lỗi hiển thị font", parent="Search",
                                evidence_count=2, examples=[])
        ]), 2

    monkeypatch.setattr(taxonomy_service, "recommend_topics", _fake_recommend)

    gen = client.post(
        "/api/taxonomies/recommend",
        json={"product_id": str(rec_env.id)},
        headers=auth,
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["pool_count"] == 2 and len(body["recommendations"]) == 1

    applied = client.post(
        "/api/taxonomies/recommend/apply",
        json={"product_id": str(rec_env.id), "topics": body["recommendations"]},
        headers=auth,
    )
    assert applied.status_code == 200, applied.text
    assert len(applied.json()["created"]) == 1

    # Re-enrich loop: clear uncategorized → released=2
    released = client.post(
        "/api/analysis/re-enrich-uncategorized",
        json={"product_id": str(rec_env.id)},
        headers=auth,
    )
    assert released.status_code == 200, released.text
    assert released.json()["released"] == 2
    with SessionLocal() as db:
        rows = db.scalars(
            select(Feedback).where(Feedback.source == "test-recommend")
        ).all()
        assert all(r.ai_analysis is None and r.analysis_run_id is None for r in rows)

    # Gọi lần 2 → 0 (đã clear hết)
    again = client.post(
        "/api/analysis/re-enrich-uncategorized",
        json={"product_id": str(rec_env.id)},
        headers=auth,
    )
    assert again.json()["released"] == 0


def test_recommend_is_pm_only(client, rec_env) -> None:
    ops = _login(client, UserRole.operations)
    resp = client.post(
        "/api/taxonomies/recommend",
        json={"product_id": str(rec_env.id)},
        headers=ops,
    )
    assert resp.status_code == 403


def test_reset_uncategorized_service_direct(rec_env) -> None:
    fid = _seed_feedback(rec_env.id, "svc-1", {"topics": [], "uncategorized": True})
    with SessionLocal() as db:
        assert analysis_service.reset_uncategorized(db, rec_env.id) >= 1
    with SessionLocal() as db:
        row = db.get(Feedback, fid)
        assert row.ai_analysis is None and row.analysis_run_id is None

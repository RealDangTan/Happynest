"""Integration test taxonomy governance — plan 23 (VoC OS §20–21).

⚠️ Marker `integration` — DB Supabase thật; KHÔNG LLM (governance thuần DB +
runner accumulate là deterministic). Seed taxonomy của test_product dọn sạch
sau test (trừ canonical gốc do migration 0010 seed — giữ nguyên).
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.feedback import Feedback
from app.models.taxonomy import Taxonomy
from app.services import taxonomy_service
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
def tax_env(test_product):
    """Sạch TOÀN BỘ taxonomy + feedback test của product trước/sau test
    (approve biến emerging thành canonical — dọn theo kind là thiếu)."""
    def _clean():
        with SessionLocal() as db:
            db.query(Taxonomy).filter(
                Taxonomy.product_id == test_product.id
            ).delete(synchronize_session=False)
            db.query(Feedback).filter(Feedback.source == "test-taxonomy").delete(
                synchronize_session=False
            )
            db.commit()

    _clean()
    yield test_product
    _clean()


def test_seed_default_taxonomy_creates_five_roots(tax_env) -> None:
    taxonomy_service.seed_default_taxonomy(SessionLocal(), tax_env.id)
    # migration 0010 đã seed → gọi lại phải idempotent (không nhân bản)
    with SessionLocal() as db:
        canonical = db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == tax_env.id,
                Taxonomy.kind == "canonical",
                Taxonomy.parent_id.is_(None),
            )
        ).all()
        names = {t.name for t in canonical}
        assert names == set(taxonomy_service.DEFAULT_ROOTS)


def test_accumulate_emerging_creates_and_increments(tax_env) -> None:
    with SessionLocal() as db:
        taxonomy_service.seed_default_taxonomy(db, tax_env.id)

        # lần 1: topic lạ → tạo emerging pending_review evidence=1
        new1 = taxonomy_service.accumulate_emerging(
            db, tax_env.id, ["Fake Citation", "Search"]
        )
        assert new1 == ["Fake Citation"]

        # lần 2: cùng topic → evidence_count tăng, KHÔNG nhân bản
        new2 = taxonomy_service.accumulate_emerging(
            db, tax_env.id, ["fake citation", "Search"]
        )
        assert new2 == []
        theme = db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == tax_env.id, Taxonomy.name == "Fake Citation"
            )
        ).one()
        assert theme.kind == "emerging"
        assert theme.status == "pending_review"
        assert theme.evidence_count == 1  # "fake citation" casefold trùng known
        assert theme.first_seen is not None


def test_review_queue_and_governance_endpoints(client, tax_env) -> None:
    auth = _login(client)
    with SessionLocal() as db:
        taxonomy_service.seed_default_taxonomy(db, tax_env.id)
        taxonomy_service.accumulate_emerging(
            db, tax_env.id, ["Fake Citation"], taxonomy_names=[]
        )

    queue = client.get(
        "/api/taxonomies/review", params={"product_id": str(tax_env.id)}, headers=auth
    ).json()
    assert queue["total"] == 1
    theme = queue["items"][0]
    assert theme["name"] == "Fake Citation"
    assert theme["status"] == "pending_review" and theme["kind"] == "emerging"

    # --- approve → canonical active ---
    dec = client.post(
        f"/api/taxonomies/review/{theme['id']}",
        json={"action": "approve"},
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["kind"] == "canonical" and dec.json()["status"] == "active"
    with SessionLocal() as db:
        assert "Fake Citation" in taxonomy_service.get_taxonomy_names(db, tax_env.id)

    # review lần 2 trên node đã duyệt → 409
    dec2 = client.post(
        f"/api/taxonomies/review/{theme['id']}",
        json={"action": "approve"},
        headers=auth,
    )
    assert dec2.status_code == 409


def test_merge_redirects_feedback_topics(client, tax_env) -> None:
    auth = _login(client)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        taxonomy_service.seed_default_taxonomy(db, tax_env.id)
        taxonomy_service.accumulate_emerging(
            db, tax_env.id, ["Hallucination"], taxonomy_names=["Search"]
        )
        theme = db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == tax_env.id, Taxonomy.name == "Hallucination"
            )
        ).one()
        target = db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == tax_env.id, Taxonomy.name == "AI Quality"
            )
        ).one()
        fb = Feedback(
            product_id=tax_env.id,
            source="test-taxonomy",
            occurred_at=now,
            raw_content="bot bia citation gia (khong PII)",
            feedback_text="bot bia citation gia",
            ai_analysis={"topics": ["Hallucination"], "sentiment": "negative"},
        )
        db.add(fb)
        db.commit()
        theme_id, target_id = theme.id, target.id

    dec = client.post(
        f"/api/taxonomies/review/{theme_id}",
        json={"action": "merge", "merge_into_id": str(target_id)},
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "merged"

    with SessionLocal() as db:
        fb = db.scalars(
            select(Feedback).where(Feedback.source == "test-taxonomy")
        ).one()
        assert fb.ai_analysis["topics"] == ["AI Quality"]
        target = db.get(Taxonomy, target_id)
        assert target.evidence_count == 1


def test_merge_requires_target(client, tax_env) -> None:
    auth = _login(client)
    with SessionLocal() as db:
        taxonomy_service.accumulate_emerging(
            db, tax_env.id, ["Orphan Theme"], taxonomy_names=[]
        )
        theme = db.scalars(
            select(Taxonomy).where(Taxonomy.name == "Orphan Theme")
        ).one()
        theme_id = theme.id

    resp = client.post(
        f"/api/taxonomies/review/{theme_id}",
        json={"action": "merge"},
        headers=auth,
    )
    assert resp.status_code == 422

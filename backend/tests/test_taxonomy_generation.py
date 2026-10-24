"""Plan 31 — GPT taxonomy generation + apply (human gate).

⚠️ Marker `integration` — DB thật; KHÔNG LLM thật (generate_proposal bị mock ở
tầng `taxonomy_service.chat_structured`). Data seed source "test-generate" tự
dọn trong fixture (self-seeding rule — taste 2026-09).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from app.schemas.taxonomy import (
    ProposedTopic,
    TaxonomyProposalOut,
    strict_taxonomy_proposal_schema,
)
from app.services import taxonomy_service
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _login(client: TestClient, account: str = "primary") -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[account], "password": TEST_PASSWORDS[account]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def gen_env(test_product):
    def _clean():
        with SessionLocal() as db:
            db.query(Taxonomy).filter(
                Taxonomy.product_id == test_product.id
            ).delete(synchronize_session=False)
            db.query(Feedback).filter(
                Feedback.source == "test-generate"
            ).delete(synchronize_session=False)
            db.commit()

    _clean()
    yield test_product
    _clean()


_FIXTURE_PROPOSAL = TaxonomyProposalOut(
    topics=[
        ProposedTopic(name="Payment", parent=None, description="mọi vấn đề thanh toán"),
        ProposedTopic(name="Payment failure", parent="Payment"),
        ProposedTopic(name="Account", parent=None),
        ProposedTopic(name="Login", parent="Account"),
    ]
)


def test_slugify_vietnamese() -> None:
    assert taxonomy_service.slugify("Thanh toán") == "thanh_toan"
    assert taxonomy_service.slugify("Payment failure") == "payment_failure"
    assert taxonomy_service.slugify("  AI Quality!  ") == "ai_quality"


def test_generate_proposal_prompt_uses_sanitized_only(gen_env, monkeypatch) -> None:
    captured: dict = {}

    def _fake_chat(system, user, schema, **kwargs):
        captured["system"] = system
        captured["user"] = user
        captured["kwargs"] = kwargs
        assert schema is TaxonomyProposalOut
        return _FIXTURE_PROPOSAL

    monkeypatch.setattr(taxonomy_service, "chat_structured", _fake_chat)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add(
            Feedback(
                product_id=gen_env.id,
                source="test-generate",
                occurred_at=now,
                # raw chứa "PII" giả — KHÔNG BAO GIỜ được lọt vào prompt
                raw_content="lien he 0900999888 de bao loi",
                feedback_text="lien he <PHONE> de bao loi",
            )
        )
        db.commit()

    with SessionLocal() as db:
        product = db.get(Product, gen_env.id)
        proposal, sample_count = taxonomy_service.generate_proposal(db, product)

    assert proposal == _FIXTURE_PROPOSAL
    assert sample_count == 1
    assert "lien he <PHONE> de bao loi" in captured["user"]
    assert "0900999888" not in captured["user"]
    assert captured["kwargs"]["call_type"].value == "taxonomy_generate"
    assert captured["kwargs"]["prompt_version"] == taxonomy_service.PROMPT_VERSION_TAXONOMY


def test_generate_proposal_stratifies_across_time_and_dedupes(gen_env, monkeypatch) -> None:
    """Prompt v5: mẫu phải phủ CẢ khoảng thời gian (không chỉ mới nhất) và
    gộp trùng lặp — payload kèm corpus_stats cho model biết bối cảnh thật."""
    import json

    captured: dict = {}

    def _fake_chat(system, user, schema, **kwargs):
        captured["user"] = user
        return _FIXTURE_PROPOSAL

    monkeypatch.setattr(taxonomy_service, "chat_structured", _fake_chat)

    now = datetime.now(timezone.utc)
    old = now - timedelta(days=120)
    rows = []
    # 3 feedback cũ + 20 feedback mới (một đợt bug wave) + 1 trùng lặp nguyên văn
    for i in range(3):
        rows.append(
            Feedback(
                product_id=gen_env.id,
                source="test-generate",
                occurred_at=old + timedelta(days=i),
                raw_content=f"old {i}",
                feedback_text=f"app crash khi mo file lan {i}",
            )
        )
    for i in range(20):
        rows.append(
            Feedback(
                product_id=gen_env.id,
                source="test-generate",
                occurred_at=now - timedelta(hours=i),
                raw_content=f"new {i}",
                feedback_text=f"bot tra loi sai thu {i}",
            )
        )
    rows.append(
        Feedback(
            product_id=gen_env.id,
            source="test-generate",
            occurred_at=now - timedelta(hours=1),
            raw_content="dup",
            feedback_text="BOT TRA LOI SAI thu 2 ",  # trùng (casefold+whitespace) bản mới
        )
    )
    with SessionLocal() as db:
        db.add_all(rows)
        db.commit()
        product = db.get(Product, gen_env.id)
        proposal, sample_count = taxonomy_service.generate_proposal(
            db, product, sample_size=6
        )

    payload = json.loads(captured["user"])
    samples = payload["sample_feedback"]
    stats = payload["corpus_stats"]
    assert sample_count == 6
    # round-robin bucket: sample đầu tiên của mỗi bucket là feedback CŨ
    # (bucket oldest được duyệt trước) — không bị wave mới nuốt hết mẫu.
    assert any("crash khi mo file" in s["text"] for s in samples)
    # trùng lặp nguyên văn bị gộp — unique_texts < tổng rows
    assert stats["unique_texts"] == 23  # 3 cũ + 20 mới (1 dup gộp)
    assert stats["duplicates_merged"] == 1
    assert stats["total_feedback_in_pool"] == 24
    assert stats["sampled"] == 6
    assert stats["time_buckets_stratified"] == 6
    assert set(s for s in stats["sources"]) == {"test-generate"}
    # mỗi sample kèm metadata thời gian/nguồn cho prompt
    assert all({"occurred_at", "source", "text"} <= set(s) for s in samples)


def test_generate_proposal_empty_corpus_raises(seeded_users) -> None:
    """Không có feedback nào → 422 từ service (không đốt LLM call bịa taxonomy).
    Product riêng để không phụ thuộc feedback sót của test khác."""
    with SessionLocal() as db:
        product = Product(
            name=f"gen-empty-{uuid.uuid4().hex[:8]}",
            owner_id=seeded_users["primary"].id,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        try:
            with pytest.raises(
                taxonomy_service.TaxonomyValidationError, match="Chưa có phản hồi"
            ):
                taxonomy_service.generate_proposal(db, product)
        finally:
            db.delete(product)
            db.commit()


def test_apply_creates_tree_slugs_and_bumps_version(gen_env) -> None:
    with SessionLocal() as db:
        version_before = db.get(Product, gen_env.id).taxonomy_version

    result = taxonomy_service.apply_proposal(
        SessionLocal(), gen_env, _FIXTURE_PROPOSAL
    )
    assert len(result["created"]) == 4
    assert result["skipped"] == 0
    assert result["taxonomy_version"] == version_before + 1

    with SessionLocal() as db:
        roots = {
            t.name: t
            for t in db.scalars(
                select(Taxonomy).where(
                    Taxonomy.product_id == gen_env.id,
                    Taxonomy.parent_id.is_(None),
                )
            ).all()
        }
        assert set(roots) == {"Payment", "Account"}
        child = db.scalars(
            select(Taxonomy).where(Taxonomy.name == "Payment failure")
        ).one()
        assert child.slug == "payment.payment_failure"
        assert child.parent_id == roots["Payment"].id
        assert child.kind == "canonical" and child.status == "active"
        assert db.get(Product, gen_env.id).taxonomy_version == version_before + 1


def test_apply_is_idempotent_skip_duplicates(gen_env) -> None:
    taxonomy_service.apply_proposal(SessionLocal(), gen_env, _FIXTURE_PROPOSAL)
    result = taxonomy_service.apply_proposal(SessionLocal(), gen_env, _FIXTURE_PROPOSAL)
    assert result["created"] == []
    assert result["skipped"] == 4


def test_apply_rejects_unknown_parent(gen_env) -> None:
    bad = TaxonomyProposalOut(
        topics=[ProposedTopic(name="Orphan", parent="Không Tồn Tại")]
    )
    with pytest.raises(ValueError, match="parent"):
        taxonomy_service.apply_proposal(SessionLocal(), gen_env, bad)


def test_ensure_slugs_backfills_legacy(gen_env) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        node = Taxonomy(
            product_id=gen_env.id,
            name="Tìm kiếm",
            kind="canonical",
            status="active",
            created_at=now,
        )
        db.add(node)
        db.commit()
        node_id = node.id

    assigned = taxonomy_service.ensure_slugs(SessionLocal(), gen_env.id)
    assert assigned >= 1
    with SessionLocal() as db:
        assert db.get(Taxonomy, node_id).slug == "tim_kiem"


def test_routes_generate_and_apply(client, gen_env, monkeypatch) -> None:
    auth = _login(client)

    def _fake_generate(db, product, *, sample_size=30, context=None):
        return _FIXTURE_PROPOSAL, 0

    monkeypatch.setattr(taxonomy_service, "generate_proposal", _fake_generate)

    gen = client.post(
        "/api/taxonomies/generate",
        json={"product_id": str(gen_env.id), "sample_size": 5},
        headers=auth,
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["proposal"] == _FIXTURE_PROPOSAL.model_dump(mode="json")

    applied = client.post(
        "/api/taxonomies/apply",
        json={"product_id": str(gen_env.id), "proposal": body["proposal"]},
        headers=auth,
    )
    assert applied.status_code == 200, applied.text
    apply_body = applied.json()
    assert len(apply_body["created"]) == 4
    assert apply_body["created"][0]["slug"]

    tree = client.get(
        "/api/taxonomies", params={"product_id": str(gen_env.id)}, headers=auth
    ).json()
    assert tree["total"] == 4


def test_other_account_cannot_generate(client, gen_env, monkeypatch) -> None:
    """Isolation 2026-10-22: account khác không generate được trên product
    của mình (404 như thể product không tồn tại)."""
    monkeypatch.setattr(taxonomy_service, "chat_structured",
                        lambda *args, **kwargs: _FIXTURE_PROPOSAL)
    other = _login(client, "secondary")
    resp = client.post(
        "/api/taxonomies/generate",
        json={"product_id": str(gen_env.id)},
        headers=other,
    )
    assert resp.status_code == 404, resp.text


def test_apply_unknown_parent_maps_422(client, gen_env) -> None:
    auth = _login(client)
    resp = client.post(
        "/api/taxonomies/apply",
        json={
            "product_id": str(gen_env.id),
            "proposal": {"topics": [{"name": "Orphan", "parent": "Ghost"}]},
        },
        headers=auth,
    )
    assert resp.status_code == 422


def test_strict_proposal_schema_matches_model() -> None:
    schema = strict_taxonomy_proposal_schema()
    props = schema["properties"]["topics"]["items"]["properties"]
    assert set(props) == set(ProposedTopic.model_fields)
    assert schema["additionalProperties"] is False


def test_unknown_product_404(client) -> None:
    auth = _login(client)
    ghost = uuid.uuid4()
    assert (
        client.post(
            "/api/taxonomies/generate", json={"product_id": str(ghost)}, headers=auth
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/taxonomies/apply",
            json={"product_id": str(ghost), "proposal": {"topics": [{"name": "A"}]}},
            headers=auth,
        ).status_code
        == 404
    )

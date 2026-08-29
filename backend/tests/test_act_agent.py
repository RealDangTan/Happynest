"""Integration test ACT layer + Gate #3 — plan 26 (VoC OS §44–52).

⚠️ Marker `integration` — DB Supabase thật; LLM MOCK (monkeypatch
`act_agent.chat_structured` — proposal cố định để assert formula/matrix/idempotency).

Kịch bản DoD §72 Phase-6:
- Generate trên insight pending → 409; approved → candidates đúng function,
  function relevance thấp bị skip;
- priority_score khớp CÔNG THỨC deterministic (không phải LLM tính);
- human override → agent value giữ nguyên + priority recompute từ human value,
  matrix quadrant đổi theo;
- rerun generate giữ action đã edit, thay action proposed;
- human thêm action (POST) → status accepted.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.action import Action
from app.models.enums import UserRole
from app.models.insight import Insight
from app.models.product import Product
from app.services import act_agent
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _proposal():
    from app.services.act_agent import ActProposalOut

    return ActProposalOut.model_validate(
        {
            "functions": [
                {"function": "ENGINEERING", "relevance": 0.96,
                 "recommendation": "Investigate citation-validation changes in v2.17",
                 "rationale": "Concentrated in v2.17", "impact": 9, "effort": 4,
                 "urgency": 9, "confidence": 0.88},
                {"function": "SUPPORT", "relevance": 0.88,
                 "recommendation": "Prepare temp guidance for customers",
                 "rationale": "Users need workaround", "impact": 5, "effort": 2,
                 "urgency": 8, "confidence": 0.92},
                {"function": "FINANCE", "relevance": 0.12, "recommendation": None},
            ]
        }
    )


@pytest.fixture()
def act_env():
    """Product dedicated + insight approved."""
    with SessionLocal() as db:
        product = db.scalars(
            select(Product).where(Product.name == "act-test-product")
        ).first()
        if product is None:
            product = Product(name="act-test-product", description="act suite")
            db.add(product)
            db.commit()
            db.refresh(product)
        db.query(Action).filter(Action.insight_id.in_(
            select(Insight.id).where(Insight.product_id == product.id)
        )).delete(synchronize_session=False)
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.commit()
        insight = Insight(
            product_id=product.id,
            title="Citation complaints in v2.17",
            finding="Search complaints up 203%, concentrated in fabricated citations",
            finding_confidence=0.91,
            hypothesis={"statement": "citation regression", "confidence": 0.67},
            affected_context={"app_version": "2.17"},
            impact=["trust_loss"],
            limitations=["coverage 72%"],
            evidence=[],
            status="approved",
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
    yield insight
    with SessionLocal() as db:
        db.query(Action).filter(Action.insight_id.in_(
            select(Insight.id).where(Insight.product_id == product.id)
        )).delete(synchronize_session=False)
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.commit()


def _login(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[UserRole.pm], "password": TEST_PASSWORDS[UserRole.pm]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _patch_llm(monkeypatch) -> None:
    from app.services import act_agent as mod

    monkeypatch.setattr(mod, "chat_structured", lambda *a, **k: _proposal())


def test_generate_blocked_on_pending_insight(client, act_env) -> None:
    auth = _login(client)
    with SessionLocal() as db:
        row = db.get(Insight, act_env.id)
        row.status = "pending"
        db.commit()
    resp = client.post(f"/api/insights/{act_env.id}/actions/generate", headers=auth)
    assert resp.status_code == 409


def test_generate_creates_candidates_and_priority_formula(client, monkeypatch, act_env) -> None:
    auth = _login(client)
    _patch_llm(monkeypatch)

    resp = client.post(f"/api/insights/{act_env.id}/actions/generate", headers=auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["actions_created"] == 2
    assert body["functions_skipped"] == ["FINANCE"]

    listing = client.get(f"/api/insights/{act_env.id}/actions", headers=auth).json()
    items = {i["function"]: i for i in listing["items"]}
    assert set(items) == {"ENGINEERING", "SUPPORT"}

    eng = items["ENGINEERING"]
    # Công thức §49 với weights mặc định: 9*0.4 + 9*0.3 + 0.88*10*0.2 + (10-4)*0.1
    expected = round(9 * 0.4 + 9 * 0.3 + 0.88 * 10 * 0.2 + 6 * 0.1, 3)
    assert eng["priority_score"] == pytest.approx(expected)
    # ENGINEERING (impact 9, effort 4) → quick_wins; matrix có id
    assert str(eng["id"]) in listing["matrix"]["quick_wins"]
    # Trong list, priority giảm dần
    scores = [i["priority_score"] for i in listing["items"]]
    assert scores == sorted(scores, reverse=True)


def test_human_override_keeps_agent_values_and_recomputes(client, monkeypatch, act_env) -> None:
    auth = _login(client)
    _patch_llm(monkeypatch)
    client.post(f"/api/insights/{act_env.id}/actions/generate", headers=auth)

    listing = client.get(f"/api/insights/{act_env.id}/actions", headers=auth).json()
    eng = next(i for i in listing["items"] if i["function"] == "ENGINEERING")

    patch = client.patch(
        f"/api/actions/{eng['id']}",
        json={"impact": 7, "effort": 7, "override_reason": "backend migration + QA"},
        headers=auth,
    )
    assert patch.status_code == 200, patch.text
    updated = patch.json()
    # Agent value GIỮ NGUYÊN (evaluation data §52)
    assert updated["impact"] == 9 and updated["effort"] == 4
    assert updated["human_impact"] == 7 and updated["human_effort"] == 7
    # priority tính lại từ HUMAN values: 7*0.4 + 9*0.3 + 0.88*10*0.2 + 3*0.1
    expected = round(7 * 0.4 + 9 * 0.3 + 0.88 * 10 * 0.2 + 3 * 0.1, 3)
    assert updated["priority_score"] == pytest.approx(expected)
    assert updated["status"] == "edited"
    # (7,7) → high impact + high effort → strategic_investments
    listing2 = client.get(f"/api/insights/{act_env.id}/actions", headers=auth).json()
    assert str(eng["id"]) in listing2["matrix"]["strategic_investments"]

    # Rerun generate: action đã human-touch GIỮ, action proposed khác được thay
    client.post(f"/api/insights/{act_env.id}/actions/generate", headers=auth)
    listing3 = client.get(f"/api/insights/{act_env.id}/actions", headers=auth).json()
    eng2 = next(i for i in listing3["items"] if i["function"] == "ENGINEERING")
    assert eng2["id"] == eng["id"]  # giữ nguyên (đã edited)
    assert eng2["human_impact"] == 7


def test_human_adds_own_action(client, act_env) -> None:
    auth = _login(client)
    resp = client.post(
        f"/api/insights/{act_env.id}/actions",
        json={
            "function": "SUPPORT",
            "recommendation": "Soạn macro trả lời cho ticket citation",
            "impact": 6,
            "effort": 2,
            "urgency": 5,
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["priority_score"] == pytest.approx(
        round(6 * 0.4 + 5 * 0.3 + 1.0 * 10 * 0.2 + 8 * 0.1, 3)
    )

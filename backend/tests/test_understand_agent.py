"""Integration test UNDERSTAND agent + Gate #2 — plan 25 Task 4.

⚠️ Marker `integration` — DB Supabase thật (checkpointer Postgres) + LLM MOCK
hoàn toàn (monkeypatch `understand_agent.nodes.chat_structured` — fake planner
gọi tool thật từ registry nên tool chạy trên data seed thật).

Kịch bản DoD §72 Phase-5:
1. Start run (question) → graph chạy nền ≥2 tool calls? (fake planner: 1 tool
   rồi synthesize) → evidence rows ghi → interrupt Gate #2;
2. Evidence id bịa trong draft bị whitelist thay bằng id thật;
3. approve → insight approved; edit → status edited + re-sanitize PII;
4. investigate_more → status investigating + graph quay lại planner;
5. reject → rejected; decision lần 2 trên thread completed → 409.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analytics.tools import TOOLS
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.services.embedder import store_embedding
from app.services.schema_registry import create_active_version
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_PRODUCT_NAME = "understand-test-product"
_DIM = 1536


def _unit_vec(idx: int) -> list[float]:
    raw = [0.0] * _DIM
    raw[idx] = 1.0
    return raw


# ------------------------------------------------------------------ fake LLM


def _fake_chat_structured(monkeypatch):
    """Fake planner/evaluator/synthesizer dispatch theo schema type.

    Planner: call 1 → tool aggregate_feedback; call ≥2 → synthesize.
    (Đảm bảo investigation có ≥1 tool call thật + evidence thật.)
    """
    from understand_agent import nodes as nodes_mod
    from understand_agent.nodes import EvaluateOut, InsightDraft, PlannerOut

    state = {"plan_calls": 0}

    def _fake(system, user, schema, **kwargs):
        if schema is PlannerOut:
            state["plan_calls"] += 1
            if state["plan_calls"] == 1:
                return PlannerOut(
                    action="tool",
                    tool="aggregate_feedback",
                    params={"group_by": "app_version"},
                    objective="Confirm trend",
                )
            return PlannerOut(action="synthesize", objective="enough evidence")
        if schema is EvaluateOut:
            return EvaluateOut(sufficient_evidence=True)
        if schema is InsightDraft:
            return InsightDraft(
                title="Test insight từ UNDERSTAND",
                finding="Fake citation complaints concentrated in v2.17",
                finding_confidence=0.9,
                hypothesis_statement="A citation regression may exist",
                hypothesis_confidence=0.6,
                affected_context={"app_version": "2.17"},
                impact=["trust_loss"],
                limitations=["Feedback evidence cannot prove causality"],
                evidence_ids=["EV-BIA-1", "EV-BIA-2"],  # bịa — whitelist phải thay
            )
        raise AssertionError(f"schema không ngờ: {schema}")

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    return state


@pytest.fixture()
def u_product():
    """Product dedicated + schema + 4 feedback có embedding tay."""
    with SessionLocal() as db:
        product = db.scalars(
            select(Product).where(Product.name == _PRODUCT_NAME)
        ).first()
        if product is None:
            product = Product(name=_PRODUCT_NAME, description="understand suite")
            db.add(product)
            db.commit()
            db.refresh(product)
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(Evidence).filter(Evidence.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(ProductSchema).filter(
            ProductSchema.product_id == product.id
        ).delete(synchronize_session=False)
        db.commit()
        create_active_version(
            db,
            product.id,
            {"fields": [{"key": "app_version", "label": "App Version", "type": "category"}]},
        )
        now = datetime.now(timezone.utc)
        for i in range(4):
            fb = Feedback(
                product_id=product.id,
                source="app_review",
                occurred_at=now - timedelta(days=i),
                raw_content=f"citation gia {i} (khong PII)",
                feedback_text=f"fake citation complaint {i}",
                data={"app_version": "2.17"},
                ai_analysis={"topics": ["Search"], "severity": "high", "sentiment": "negative", "confidence": 0.9},
            )
            db.add(fb)
            db.flush()
            store_embedding(db, fb, _unit_vec(0))
        db.commit()
    yield product
    with SessionLocal() as db:
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(Evidence).filter(Evidence.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(ProductSchema).filter(
            ProductSchema.product_id == product.id
        ).delete(synchronize_session=False)
        db.commit()


def _login(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[UserRole.pm], "password": TEST_PASSWORDS[UserRole.pm]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _wait_for_interrupt(client, auth, run_id: str, timeout_s: float = 60) -> dict:
    """Poll GET status tới khi pending_approval xuất hiện (graph chạy nền)."""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        body = client.get(f"/api/agent/runs/{run_id}", headers=auth).json()
        last = body
        if body.get("pending_approval"):
            return body
        time.sleep(2)
    raise AssertionError(f"interrupt không xuất hiện trong {timeout_s}s: {last}")


def test_full_understand_flow_approve(client, monkeypatch, u_product) -> None:
    auth = _login(client)
    _fake_chat_structured(monkeypatch)

    resp = client.post(
        "/api/agent/runs",
        json={"product_id": str(u_product.id), "question": "Why are citation complaints up?"},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    body = _wait_for_interrupt(client, auth, run_id)
    payload = body["pending_approval"]
    assert payload["insight"]["title"] == "Test insight từ UNDERSTAND"
    # Evidence thật (không phải EV-BIA bịa)
    ev_ids = [e["evidence_id"] for e in payload["evidence"]]
    assert ev_ids and all(e != "EV-BIA-1" for e in ev_ids)

    # Evidence rows đã ghi DB
    with SessionLocal() as db:
        ev_count = len(
            db.scalars(select(Evidence).where(Evidence.run_id == uuid.UUID(run_id))).all()
        )
        assert ev_count >= 1

    # --- Gate #2: approve ---
    dec = client.post(
        f"/api/agent/runs/{run_id}/decision",
        json={"action": "approve", "reason": "solid"},
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["final_status"] == "approved"

    # Insight approved + evidence refs mở rộng trong GET /insights
    listing = client.get(
        "/api/insights", params={"product_id": str(u_product.id)}, headers=auth
    ).json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["status"] == "approved"
    assert item["evidence"] and item["evidence"][0]["statement"].startswith("aggregate_feedback")
    assert item["hypothesis"]["statement"] == "A citation regression may exist"

    # decision lần 2 trên thread completed → 409
    dec2 = client.post(
        f"/api/agent/runs/{run_id}/decision",
        json={"action": "reject"},
        headers=auth,
    )
    assert dec2.status_code == 409


def test_edit_resanitizes_pii(client, monkeypatch, u_product) -> None:
    auth = _login(client)
    _fake_chat_structured(monkeypatch)

    resp = client.post(
        "/api/agent/runs",
        json={"product_id": str(u_product.id), "question": "What changed this month?"},
        headers=auth,
    )
    run_id = resp.json()["run_id"]
    _wait_for_interrupt(client, auth, run_id)

    dec = client.post(
        f"/api/agent/runs/{run_id}/decision",
        json={
            "action": "edit",
            "edited_insight": {
                "title": "Insight đã sửa",
                "finding": "Liên hệ admin@example.com để báo lỗi citation",
            },
        },
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["final_status"] == "edited"

    with SessionLocal() as db:
        insight = db.scalars(
            select(Insight).where(Insight.product_id == u_product.id)
        ).one()
        assert insight.status == "edited"
        assert insight.title == "Insight đã sửa"
        # PII bị RE-SANITIZE trước persist — email bị mask
        assert "admin@example.com" not in insight.finding


def test_investigate_more_returns_to_planner(client, monkeypatch, u_product) -> None:
    auth = _login(client)
    state = _fake_chat_structured(monkeypatch)

    resp = client.post(
        "/api/agent/runs",
        json={"product_id": str(u_product.id), "question": "Any emerging issue?"},
        headers=auth,
    )
    run_id = resp.json()["run_id"]
    _wait_for_interrupt(client, auth, run_id)

    dec = client.post(
        f"/api/agent/runs/{run_id}/decision",
        json={"action": "investigate_more", "reason": "cần dữ liệu segmentation"},
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    # fake planner lần 2 → synthesize ngay → interrupt thứ 2
    body = _wait_for_interrupt(client, auth, run_id)
    assert body["pending_approval"]["insight"]["title"]

    # approve để kết thúc sạch
    dec2 = client.post(
        f"/api/agent/runs/{run_id}/decision", json={"action": "approve"}, headers=auth
    )
    assert dec2.status_code == 200

    with SessionLocal() as db:
        insights = db.scalars(
            select(Insight).where(Insight.product_id == u_product.id)
        ).all()
        assert len(insights) >= 1  # investigate_more tạo insight mới ở vòng 2

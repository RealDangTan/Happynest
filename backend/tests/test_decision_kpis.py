"""Integration test Phase 27 — decision memory + impact check + KPIs.

⚠️ Marker `integration` — DB Supabase thật; KHÔNG LLM.

Phủ: decision_logs hook qua ACT override; impact_service đo trước/sau + idempotent;
GET /api/reports/kpis shape đầy đủ 3 gate.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.action import Action
from app.models.decision_log import DecisionLog
from app.models.enums import BusinessFunction, UserRole
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.models.product import Product
from app.services import act_agent
from app.services.impact_service import run_impact_checks
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


@pytest.fixture()
def kpi_env():
    """Product dedicated + insight approved + 1 action accepted + feedback đủ
    tuổi để đo impact (before window ≥1 row, after window ≥1 row)."""
    with SessionLocal() as db:
        product = db.scalars(
            select(Product).where(Product.name == "kpi-test-product")
        ).first()
        if product is None:
            product = Product(name="kpi-test-product", description="kpi suite")
            db.add(product)
            db.commit()
            db.refresh(product)
        # dọn rác lần trước
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        actions = db.scalars(
            select(Action).where(Action.insight_id.in_(
                select(Insight.id).where(Insight.product_id == product.id)
            ))
        ).all()
        for a in actions:
            db.delete(a)
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.commit()

        insight = Insight(
            product_id=product.id,
            title="KPI test insight",
            finding="finding text",
            finding_confidence=0.9,
            hypothesis=None,
            affected_context={"app_version": "2.17"},
            impact=["trust_loss"],
            limitations=[],
            evidence=[],
            status="approved",
        )
        db.add(insight)
        db.flush()
        now = datetime.now(timezone.utc)
        # action 'created' 10 ngày trước (đủ tuổi window 7 ngày)
        action = Action(
            insight_id=insight.id,
            function=BusinessFunction.ENGINEERING,
            recommendation="fix it",
            rationale="r",
            impact=8,
            effort=3,
            urgency=7,
            confidence=0.9,
            priority_score=0.0,
            status="accepted",
            created_at=now - timedelta(days=10),
        )
        act_agent.recompute_priority(action)
        db.add(action)
        # feedback match affected_context: 2 trước, 3 sau mốc action
        for i, days_ago in enumerate([12, 11, 8, 7, 6]):
            fb = Feedback(
                product_id=product.id,
                source="kpi",
                occurred_at=now - timedelta(days=days_ago),
                raw_content=f"row {i} (khong PII)",
                feedback_text=f"row {i}",
                data={"app_version": "2.17"},
            )
            db.add(fb)
        # 1 row KHÔNG match (app_version khác) → không đếm
        db.add(
            Feedback(
                product_id=product.id,
                source="kpi",
                occurred_at=now - timedelta(days=6),
                raw_content="other (khong PII)",
                feedback_text="other",
                data={"app_version": "2.16"},
            )
        )
        db.commit()
        db.refresh(action)
        db.refresh(insight)
    yield action
    with SessionLocal() as db:
        from app.models.impact_check import ImpactCheck

        db.query(ImpactCheck).filter(ImpactCheck.action_id == action.id).delete(
            synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(Action).filter(Action.insight_id.in_(
            select(Insight.id).where(Insight.product_id == product.id)
        )).delete(synchronize_session=False)
        db.query(Insight).filter(Insight.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(DecisionLog).filter(
            DecisionLog.subject_id == action.id
        ).delete(synchronize_session=False)
        db.commit()


def _login(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[UserRole.pm], "password": TEST_PASSWORDS[UserRole.pm]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_impact_check_measures_before_after_and_idempotent(kpi_env) -> None:
    with SessionLocal() as db:
        results = run_impact_checks(db)
        assert len(results) == 1
        r = results[0]
        assert r["before_count"] == 2  # 2 row match trong window TRƯỚC action
        assert r["after_count"] == 3   # 3 row match trong window SAU action
        assert r["delta_ratio"] == pytest.approx(0.5)

        # idempotent: chạy lại → không đo lần 2
        assert run_impact_checks(db) == []


def test_patch_action_writes_decision_log(client, kpi_env) -> None:
    auth = _login(client)
    patch = client.patch(
        f"/api/actions/{kpi_env.id}",
        json={"impact": 5, "override_reason": "KPI test override"},
        headers=auth,
    )
    assert patch.status_code == 200, patch.text
    with SessionLocal() as db:
        log = db.scalars(
            select(DecisionLog).where(
                DecisionLog.subject_type == "action",
                DecisionLog.subject_id == kpi_env.id,
            )
        ).one()
        assert log.agent_value["impact"] == 8       # agent value giữ nguyên
        assert log.human_value["human_impact"] == 5  # human override ghi nhận
        assert log.reviewer_id is not None           # từ token


def test_kpis_endpoint_shape_and_values(client, kpi_env) -> None:
    auth = _login(client)
    # đo impact trước để KPI impact non-zero
    with SessionLocal() as db:
        run_impact_checks(db)

    # override action qua API (Gate #3) → agreement/displacement đo được
    patch = client.patch(
        f"/api/actions/{kpi_env.id}",
        json={"impact": 5, "override_reason": "kpi test"},
        headers=auth,
    )
    assert patch.status_code == 200, patch.text

    body = client.get("/api/reports/kpis", headers=auth).json()
    expected_keys = {
        "generated_at", "time_to_listen_median_s", "time_to_insight_median_s",
        "time_to_action_median_s", "insights_total", "insights_with_action",
        "pct_insight_with_action", "insight_hitl_count", "insight_auto_count",
        "insight_evidence_grounding_pct", "mapping_total", "mapping_accepted",
        "actions_total", "actions_accepted", "pct_action_accepted",
        "actions_overridden", "impact_agreement", "effort_agreement",
        "matrix_displacement_avg", "impact",
    }
    assert set(body) == expected_keys, set(body) ^ expected_keys
    assert body["actions_total"] >= 1
    assert body["pct_action_accepted"] > 0
    # action của test bị override impact → agreement/displacement đo được
    assert body["actions_overridden"] >= 1
    assert body["impact_agreement"] is not None
    assert body["matrix_displacement_avg"] is not None
    assert body["impact"]["checks_count"] >= 1

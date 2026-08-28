"""Integration test GET /api/reports/kpis — phase 20 Task 2 Step 2.2.

Chạy: `uv run pytest -m integration tests/test_reports_kpis_integration.py -v`

Data demo thật + 1 insight approved giả kèm draft + insight_review row (marker
prefix ``kpit-`` — GUARD skip khi còn rác lạ, teardown xoá đúng bộ vừa tạo,
FK order như test_impact_service). Assert từng field kiểu/hợp lý: median > 0
khi có mốc, pct ∈ [0,100], hitl+auto = finalized. Zero-LLM: service không
import llm_client (cùng tinh thần phase 16) — assert tĩnh bằng dir() module.
"""

from datetime import datetime, timedelta, timezone
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.db.session import SessionLocal
from app.models.action_draft import ActionDraft
from app.models.cluster import Cluster
from app.models.enums import DraftKind, ReviewStatus, UserRole
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_REF_PREFIX = "kpit-"
_TITLE_PREFIX = "[kpit-"
_plant_seq = count()

_KPIS_FIELDS = {
    "generated_at",
    "time_to_listen_median_s",
    "time_to_insight_median_s",
    "time_to_action_median_s",
    "insights_total",
    "insights_with_action",
    "pct_insight_with_action",
    "hitl_count",
    "auto_count",
    "hitl_share",
    "impact",
}
_IMPACT_FIELDS = {"checks_count", "avg_delta_ratio"}


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _count_stray() -> int:
    with SessionLocal() as db:
        fb = int(
            db.execute(
                text("SELECT count(*) FROM feedbacks WHERE external_ref LIKE :p"),
                {"p": _REF_PREFIX + "%"},
            ).scalar_one()
        )
        ins = int(
            db.execute(
                text("SELECT count(*) FROM insights WHERE title LIKE :p"),
                {"p": _TITLE_PREFIX + "%"},
            ).scalar_one()
        )
        return fb + ins


@pytest.fixture()
def planted_insight():
    """Insight approved + draft + review row để KPI có mốc HITL thật."""
    if _count_stray():
        pytest.skip("DB dùng chung còn row kpit-* chưa dọn — bỏ chạy.")

    from app.models.enums import DraftStatus

    now = datetime.now(timezone.utc)
    cname = f"{_TITLE_PREFIX}Cụm wifi rớt #{next(_plant_seq)}"
    ins_id = None
    with SessionLocal() as db:
        db.add(
            Cluster(
                name=cname,
                summary="than wifi.",
                feedback_count=1,
                first_seen=now - timedelta(days=20),
                last_seen=now - timedelta(days=10),
                current_count=1,
                previous_count=0,
                growth_ratio=2.0,
                is_emerging=False,
                is_spike=False,
                suggested_priority=0.5,
            )
        )
        db.flush()
        cid = db.scalar(select(Cluster.id).where(Cluster.name == cname)).one()

        db.add(
            Feedback(
                external_ref=f"{_REF_PREFIX}member",
                source="unit-test",
                created_at=now - timedelta(days=11),
                raw_content="raw kpi test (không ra khỏi biên sanitize)",
                sanitized_content="wifi rớt.",
                cluster_id=cid,
            )
        )
        ins = Insight(
            cluster_id=cid,
            title=_TITLE_PREFIX + "Fix wifi ngay",
            summary="wifi rớt nhiều.",
            suggested_action="Nâng băng thông.",
            evidence_ids=[],
            review_status=ReviewStatus.approved,
            created_at=now - timedelta(days=9),
        )
        db.add(ins)
        db.flush()
        ins_id = ins.id
        db.add(
            ActionDraft(
                insight_id=ins_id,
                kind=DraftKind.draft_ticket,
                body="ticket body",
                status=DraftStatus.draft,
                created_at=now - timedelta(days=8),
            )
        )
        db.add(
            InsightReview(
                insight_id=ins_id,
                original_value={"title": "Fix wifi ngay"},
                action="approve",
                reason="đúng vấn đề",
                reviewer_id=db.scalar(select(text("SELECT id FROM users LIMIT 1"))),
            )
        )
        db.commit()

    yield

    with SessionLocal() as db:
        db.execute(delete(InsightReview).where(InsightReview.insight_id == ins_id))
        db.execute(delete(ActionDraft).where(ActionDraft.insight_id == ins_id))
        db.execute(delete(Insight).where(Insight.id == ins_id))
        db.execute(delete(Feedback).where(Feedback.external_ref.like(_REF_PREFIX + "%")))
        db.execute(delete(Cluster).where(Cluster.name == cname))
        db.commit()
        assert _count_stray() == 0


def test_kpis_shape_and_reasonable_values(client: TestClient, planted_insight) -> None:
    auth = _login(client)
    resp = client.get("/api/reports/kpis", headers=auth)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert set(body) == _KPIS_FIELDS, set(body) ^ _KPIS_FIELDS
    assert set(body["impact"]) == _IMPACT_FIELDS

    for key in (
        "time_to_listen_median_s",
        "time_to_insight_median_s",
        "time_to_action_median_s",
    ):
        assert body[key] is None or body[key] >= 0, body[key]

    total = body["insights_total"]
    assert total >= 1, "fixture insight phải được nhìn thấy"
    assert 0 <= body["insights_with_action"] <= total
    assert 0 <= body["pct_insight_with_action"] <= 100
    assert 0 <= body["hitl_share"] <= 100
    assert body["hitl_count"] >= 1, "insight plant có review row → hitl"
    assert body["hitl_count"] + body["auto_count"] <= total

    assert body["impact"]["checks_count"] >= 0
    assert body["impact"]["avg_delta_ratio"] is None or -1.0 <= body["impact"][
        "avg_delta_ratio"
    ] <= 10.0

    # fixture plant time_to_action ≈ 1 ngày (8d trước, insight 9d trước)
    assert body["time_to_action_median_s"] is not None, "plant có draft → mốc tồn tại"


def test_kpis_no_llm_imports() -> None:
    """Service reports thuần SQL — module không được tham chiếu llm_client."""
    import app.services.reports as reports_mod

    assert "llm_client" not in dir(reports_mod)
    source = open(reports_mod.__file__, encoding="utf-8").read()
    assert "llm_client" not in source and "langfuse" not in source


def test_kpis_requires_auth(client: TestClient) -> None:
    """Client chưa login → 401 (guard router-level)."""
    assert client.get("/api/reports/kpis").status_code == 401

"""Integration test clusters API trên data demo thật — plan 14 §3 Task 4.

Chạy: `uv run pytest -m integration tests/test_clusters_api_integration.py -v`
Cần Supabase reachable (autouse fixture sẽ SKIP khi offline) + LLM key cho
call naming (2 lượt run = 2 call — đúng thiết kế kiềm chế tín dụng của plan).

Dùng 22 row demo đã có embedding từ run `9c6687bc`; KHÔNG seed thêm row.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.cluster import Cluster
from app.models.enums import UserRole
from app.models.feedback import Feedback
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_C1_FIELDS = {
    "id", "name", "summary", "feedback_count", "first_seen", "last_seen",
    "current_count", "previous_count", "growth_ratio", "is_emerging",
    "is_spike", "suggested_priority", "sample_feedback_ids",
}


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _embedded_count() -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.embedding.is_not(None))
        )


def test_clusters_run_then_list_idempotent(client: TestClient) -> None:
    auth = _login(client)
    embedded_total = _embedded_count()
    assert embedded_total > 0, "data demo phải có sẵn embedding (run 9c6687bc)"

    # ---- Run 1: POST /api/clusters/run ----
    r1 = client.post("/api/clusters/run", headers=auth)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert set(body1) == {"clusters_upserted", "assigned_count",
                          "unassigned_count", "duration_ms"}
    assert body1["duration_ms"] >= 0
    # C5: mọi row có embedding nằm hết trong assigned hoặc unassigned
    assert (
        body1["assigned_count"] + body1["unassigned_count"] == embedded_total
    ), body1

    with SessionLocal() as db:
        n_clusters_1 = db.scalar(select(func.count()).select_from(Cluster))

    # ---- GET /api/clusters shape C1 field-by-field + sort mặc định ----
    rg = client.get("/api/clusters", headers=auth)
    assert rg.status_code == 200, rg.text
    items = rg.json()["items"]
    assert len(items) == n_clusters_1
    for item in items:
        assert set(item) == _C1_FIELDS, set(item) ^ _C1_FIELDS
        assert len(item["sample_feedback_ids"]) <= 5
        assert item["first_seen"] <= item["last_seen"]
        assert item["feedback_count"] >= item["current_count"]
    counts = [i["feedback_count"] for i in items]
    assert counts == sorted(counts, reverse=True), "mặc định sort feedback_count desc"

    # ---- Sort growth_ratio / recent đúng thứ tự ----
    rr = client.get("/api/clusters", params={"sort": "growth_ratio"}, headers=auth)
    ratios = [i["growth_ratio"] for i in rr.json()["items"]]
    assert ratios == sorted(ratios, reverse=True)

    rs = client.get("/api/clusters", params={"sort": "recent"}, headers=auth)
    seen = [i["last_seen"] for i in rs.json()["items"]]
    assert seen == sorted(seen, reverse=True)

    # ---- Rerun lần 2: idempotence thật trên Supabase ----
    r2 = client.post("/api/clusters/run", headers=auth)
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["clusters_upserted"] == body1["clusters_upserted"], (
        "số cụm giữa 2 run phải ổn định (cùng data, cùng thuật toán)"
    )
    with SessionLocal() as db:
        n_clusters_2 = db.scalar(select(func.count()).select_from(Cluster))
    assert n_clusters_2 == n_clusters_1, "rerun không được nhân bản row cluster"
    # membership không mồ côi: mọi feedback.cluster_id trỏ cluster tồn tại
    with SessionLocal() as db:
        orphan = db.scalar(
            select(func.count())
            .select_from(Feedback)
            .where(
                Feedback.cluster_id.is_not(None),
                Feedback.cluster_id.not_in(select(Cluster.id)),
            )
        )
    assert orphan == 0


def test_clusters_endpoints_require_auth(client: TestClient) -> None:
    """Guard router-level như feedback router: không credentials → 401."""
    assert client.get("/api/clusters").status_code == 401
    assert client.post("/api/clusters/run").status_code == 401

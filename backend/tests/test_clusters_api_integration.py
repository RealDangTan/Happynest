"""Integration test clusters API — plan 14 §3 Task 4; reshape 2026-08-28.

Chạy: `uv run pytest -m integration tests/test_clusters_api_integration.py -v`
Cần Supabase reachable (autouse fixture sẽ SKIP khi offline) + LLM key cho
call naming (2 lượt run = 2 call — đúng thiết kế kiềm chế tín dụng của plan).

Reshape: data demo cũ đã bị migration 0008 wipe → suite TỰ SEED 12 row demo
(2 cụm tách biệt + vector tay, KHÔNG gọi embeddings API) rồi dọn sạch.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.cluster import Cluster
from app.models.enums import UserRole
from app.models.feedback import Feedback
from app.services.embedder import store_embedding
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_C1_FIELDS = {
    "id", "name", "summary", "feedback_count", "first_seen", "last_seen",
    "current_count", "previous_count", "growth_ratio", "is_emerging",
    "is_spike", "suggested_priority", "sample_feedback_ids",
}

_SEED_SOURCE = "test-clusters-api"
_DIM = 1536


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _unit_vec(idx: int) -> list[float]:
    raw = [0.0] * _DIM
    raw[idx] = 1.0
    return raw


@pytest.fixture()
def demo_rows(test_product):
    """Seed 12 row có embedding tay (2 cụm × 6, vector đơn vị trực giao)."""
    now = datetime.now(timezone.utc)
    ids: list = []
    with SessionLocal() as db:
        for i in range(12):
            fb = Feedback(
                product_id=test_product.id,
                source=_SEED_SOURCE,
                source_record_id=f"clustersapi-{i:02d}",
                occurred_at=now - timedelta(days=i % 5),
                raw_content=f"noi dung demo {i} cho test clusters (khong PII)",
                feedback_text=f"demo {i}",
                ai_analysis={"topics": [f"topic-{i % 2}"], "severity": "low", "sentiment": "neutral"},
            )
            db.add(fb)
            db.flush()
            store_embedding(db, fb, _unit_vec(0 if i < 6 else 1))
            ids.append(fb.id)
        db.commit()
    yield ids
    with SessionLocal() as db:
        db.query(Feedback).filter(Feedback.source == _SEED_SOURCE).delete(
            synchronize_session=False
        )
        db.commit()


def _embedded_count() -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.embedding.is_not(None))
        )


def test_clusters_run_then_list_idempotent(client: TestClient, demo_rows) -> None:
    auth = _login(client)
    embedded_total = _embedded_count()
    assert embedded_total >= 12, "seed phải tạo đủ row có embedding"

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

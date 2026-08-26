"""Integration tests insights API — Phase 15 Task 3 (plan 15).

Mock LLM ở mức service (monkeypatch `app.services.insight.chat_structured`) —
integration chỉ chứng minh đường HTTP→DB→contract, KHÔNG đốt tín dụng thật.

Cụm giả + member được COMMIT vào DB dev dùng chung (route mở SessionLocal riêng
nên rollback fixture không thấy) → teardown xoá theo id cụm vừa tạo. POST
/insights/run REPLACE-ALL toàn bảng insights — hiện DB dev insights rỗng nên vô
hại; teardown vẫn xoá insight của cụm test.

Chạy:  uv run pytest -m integration tests/test_insights_api_integration.py -v
"""

import os
from datetime import datetime, timedelta, timezone
from json import loads
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

import app.services.insight as insight_service
from app.db.session import SessionLocal
from app.models.cluster import Cluster
from app.models.enums import UserRole
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.schemas.insight import InsightDraft
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_C2_ITEM_FIELDS = {
    "id", "cluster_id", "title", "summary", "suggested_action",
    "evidence", "review_status",
}
_EVIDENCE_FIELDS = {"feedback_id", "snippet", "severity", "created_at"}


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def seeded_cluster():
    """1 cụm ưu tiên cao + 3 member commit thật; teardown xoá dấu vết."""
    cid = uuid4()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add(
            Cluster(
                id=cid,
                name="ins-it-cụm integration",
                summary="cụm test integration",
                feedback_count=3,
                first_seen=now - timedelta(days=2),
                last_seen=now - timedelta(days=1),
                current_count=3,
                previous_count=0,
                growth_ratio=9.99,
                is_emerging=True,
                is_spike=False,
                suggested_priority=0.9,
            )
        )
        for i in range(3):
            db.add(
                Feedback(
                    external_ref=f"ins-it-{cid.hex[:8]}-{i}",
                    source="unit-test",
                    created_at=now - timedelta(hours=i),
                    raw_content=f"RAW-integration-{i} never leaves sanitize boundary",
                    sanitized_content=f"nội dung sanitized mẫu {i}",
                    severity=("critical", "high", "medium")[i],
                    sentiment="negative",
                    confidence=round(0.9 - i * 0.1, 2),
                    cluster_id=cid,
                )
            )
        db.commit()
    yield cid
    with SessionLocal() as db:
        db.execute(delete(Insight).where(Insight.cluster_id == cid))
        db.execute(delete(Feedback).where(Feedback.cluster_id == cid))
        db.execute(delete(Cluster).where(Cluster.id == cid))
        db.commit()


def _mock_llm(monkeypatch, factory=None) -> list[str]:
    calls: list[str] = []

    def fake(system, user, schema, **kwargs):
        calls.append(user)
        if factory is not None:
            return factory(len(calls) - 1, user)
        return InsightDraft(
            title="Tiêu đề integration",
            summary="Tóm tắt integration.",
            suggested_action="Hành động integration.",
            evidence_feedback_ids=[],
        )

    monkeypatch.setattr(insight_service, "chat_structured", fake)
    return calls


def _factory_one_real_one_fake(_n: int, user: str) -> InsightDraft:
    """LLM đề xuất 1 id THẬT (từ payload) + 1 id bịa → server phải lọc cái bịa."""
    payload = loads(user)
    real = UUID(payload["snippets"][0]["feedback_id"])
    return InsightDraft(
        title="Tiêu đề integration",
        summary="Tóm tắt integration.",
        suggested_action="Hành động integration.",
        evidence_feedback_ids=[real, uuid4()],
    )


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/insights").status_code == 401
    assert client.post("/api/insights/run").status_code == 401


def test_run_409_when_no_clusters(client: TestClient, monkeypatch) -> None:
    _mock_llm(monkeypatch)
    auth = _login(client)
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Cluster)):
            pytest.skip(
                "DB dev đang có cụm — điều kiện 409 yêu cầu bảng clusters rỗng "
                "(P5 nạp data demo nhóm chủ đề thì test này phải đổi chiến lược)"
            )
    r = client.post("/api/insights/run", headers=auth)
    assert r.status_code == 409, r.text
    assert "clusters/run" in r.json()["detail"]


def test_run_then_get_c2_shape_then_rerun_no_duplicate(
    client: TestClient, monkeypatch, seeded_cluster
) -> None:
    auth = _login(client)
    calls = _mock_llm(monkeypatch, _factory_one_real_one_fake)

    # ---- POST /api/insights/run lần 1 (C6) ----
    r1 = client.post("/api/insights/run", headers=auth)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["insights_generated"] == 1
    assert body1["duration_ms"] >= 0
    assert len(calls) == 1                      # 1 cụm → đúng 1 call

    # ---- GET /api/insights shape C2 field-by-field ----
    rg = client.get("/api/insights", headers=auth)
    assert rg.status_code == 200, rg.text
    items = rg.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert set(item) == _C2_ITEM_FIELDS, set(item) ^ _C2_ITEM_FIELDS
    assert item["cluster_id"] == str(seeded_cluster)
    assert item["title"] and item["summary"] and item["suggested_action"]

    evs = item["evidence"]
    assert len(evs) == 1                        # id bịa bị whitelist lọc
    ev = evs[0]
    assert set(ev) == _EVIDENCE_FIELDS, set(ev) ^ _EVIDENCE_FIELDS
    assert "RAW-" not in ev["snippet"]          # PII boundary phía response
    assert ev["snippet"].startswith("nội dung sanitized mẫu")
    assert ev["severity"] in {"critical", "high", "medium", "low"}

    # evidence trỏ tới feedback THẬT thuộc đúng cụm (whitelist từ DB)
    with SessionLocal() as db:
        member_ids = set(
            db.scalars(
                select(Feedback.id).where(Feedback.cluster_id == seeded_cluster)
            ).all()
        )
    assert UUID(ev["feedback_id"]) in member_ids
    assert ev["created_at"]

    # ---- POST lần 2: replace-all không nhân bản ----
    r2 = client.post("/api/insights/run", headers=auth)
    assert r2.status_code == 200, r2.text
    rg2 = client.get("/api/insights", headers=auth)
    items2 = rg2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["id"] != item["id"]        # row mới thay row cũ
    assert items2[0]["evidence"][0]["feedback_id"] == ev["feedback_id"]


@pytest.mark.skipif(
    not os.environ.get("EVIDENCE_LLM_LIVE"),
    reason="Evidence LLM thật cho luận văn — chỉ bật khi EVIDENCE_LLM_LIVE=1",
)
def test_live_evidence_manual(client: TestClient, seeded_cluster) -> None:
    """KHÔNG mock — đốt tín dụng thật. Chụp JSON response + llm_call_logs."""
    auth = _login(client)
    r = client.post("/api/insights/run", headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    print("\nLIVE run:", body)

    rg = client.get("/api/insights", headers=auth)
    assert rg.status_code == 200
    items = rg.json()["items"]
    print("LIVE GET:", __import__("json").dumps(items, ensure_ascii=False, indent=2))
    assert items and items[0]["evidence"], "live run phải sinh ≥1 insight có evidence"

    from app.models.enums import LlmCallType
    from app.models.llm_call_log import LlmCallLog

    with SessionLocal() as db:
        n = db.scalar(
            select(func.count())
            .select_from(LlmCallLog)
            .where(LlmCallLog.call_type == LlmCallType.generate_insight)
        )
    assert n and n >= 1, "llm_call_logs phải có dòng generate_insight"

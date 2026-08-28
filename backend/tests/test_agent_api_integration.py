"""Integration test agent API trên DB dev dùng chung — phase 19 Task 4 Step 4.5.

Chạy: `uv run pytest -m integration tests/test_agent_api_integration.py -v`

Kịch bản plan: fake-LLM scripted (router lần lượt chọn metrics → quotes →
precedents → synthesize; draft có evidence id hợp lệ) chạy FULL qua HTTP
(TestClient + thread nền thật + AsyncPostgresSaver Supabase) tới interrupt →
POST decision approve → assert Insight + 2 ActionDraft + InsightReview ĐÚNG
1 BỘ.

Isolation (bài học sự cố ô nhiễm 2026-08-26): mọi row plant gắn marker
external_ref ``agapi-`` / title prefix; GUARD skip khi thấy row lạ khớp
predicate (DB đang bận bởi runner khác) — test KHÔNG bao giờ đụng data của
tiến trình khác. LLM thật không bị gọi: patch nodes.chat_structured +
2 điểm embed_one.
"""

from __future__ import annotations

import time
import uuid as uuid_mod
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.action_draft import ActionDraft
from app.models.analysis_run import AnalysisRun
from app.models.cluster import Cluster
from app.models.enums import ReviewStatus, Severity, UserRole
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_REF_PREFIX = "agapi-"
_TITLE_PREFIX = "[agapi-test]"
_POLL_SEC = 300
_POLL_STEP = 4


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _count_stray(db) -> int:
    return int(
        db.execute(
            text("SELECT count(*) FROM feedbacks WHERE external_ref LIKE :p"),
            {"p": _REF_PREFIX + "%"},
        ).scalar_one()
    )


@pytest.fixture()
def planted(monkeypatch):
    """Plant cụm giả + members; GUARD skip nếu DB còn rác/lạ cùng marker;
    patch mọi seam tốn LLM. Trả dict id để test + cleanup dùng."""
    from happynest_agent import nodes as nodes_mod
    from happynest_agent.tools import precedents as precedents_mod
    from app.models.enums import RunStatus

    with SessionLocal() as db:
        stray = _count_stray(db)
        if stray:
            pytest.skip(f"DB dùng chung còn {stray} row agapi-* chưa dọn — bỏ chạy.")

        # Quarantine run — claim members NGAY LÚC TẠO (bài học ô nhiễm: runner
        # deterministic song song nhặt mọi row analysis_run_id IS NULL).
        s = get_settings()
        qrun = AnalysisRun(
            pipeline_version="test-quarantine",
            llm_model=s.LLM_MODEL,
            prompt_version=s.PROMPT_VERSION,
            embedding_model=s.EMBEDDING_MODEL,
            total_count=0,
        )
        qrun.status = RunStatus.failed
        db.add(qrun)
        db.flush()

        cid = uuid_mod.uuid4()
        now = datetime.now(timezone.utc)
        db.add(
            Cluster(
                id=cid,
                name=_TITLE_PREFIX + "App chậm lúc giờ cao điểm",
                summary="Người dùng than phản hồi chậm.",
                feedback_count=3,
                current_count=3,
                previous_count=0,
                growth_ratio=5.0,
                first_seen=now - timedelta(days=7),
                last_seen=now,
                is_emerging=True,
                is_spike=False,
                suggested_priority=0.9,  # ≥ 0.70 → risk gate HIGH → interrupt
            )
        )

        member_ids = []
        for i in range(3):
            fid = uuid_mod.uuid4()
            member_ids.append(fid)
            db.add(
                Feedback(
                    id=fid,
                    external_ref=f"{_REF_PREFIX}{i}",
                    source="import",
                    created_at=now,
                    raw_content=f"RAW-CONTENT-SEED-{i} (không bao giờ ra ngoài)",
                    sanitized_content=f"App rất chậm vào buổi tối số {i}.",
                    severity=Severity.high if i == 0 else Severity.medium,
                    categories=["hiệu năng"],
                    review_status=ReviewStatus.unreviewed,
                    analysis_run_id=qrun.id,  # claim — runner thật không nhặt
                    cluster_id=cid,  # member của cụm plant — metrics/quotes đọc được
                )
            )
        db.commit()

    dim = get_settings().EMBEDDING_DIM

    def fake_embed(text_: str) -> list[float]:
        return [0.0] * dim

    monkeypatch.setattr(precedents_mod, "embed_one", fake_embed)
    monkeypatch.setattr(nodes_mod, "embed_one", fake_embed)

    route_script = [
        "get_cluster_metrics",
        "fetch_evidence_quotes",
        "retrieve_similar_insights",
        "synthesize",
    ]

    state = {
        "cluster_id": cid,
        "member_ids": member_ids,
        "qrun_id": qrun.id,
        "run_id": None,
        "llm_calls": 0,
    }

    def fake_chat(system, user, schema, **kwargs):
        name = getattr(schema, "__name__", "?")
        state["llm_calls"] += 1  # đếm thay llm_call_logs (fake không ghi log)
        if name == "RouteDecision":
            nxt = route_script.pop(0)
            return schema.model_validate({"next": nxt, "rationale": "scripted"})
        if name == "InsightDraft":
            return schema.model_validate(
                {
                    "title": _TITLE_PREFIX + "Hiệu năng tối giảm mạnh",
                    "summary": "Cụm hiệu năng tăng nhanh với severity cao.",
                    "suggested_action": "Ưu tiên rà profiling server buổi tối.",
                    "evidence_feedback_ids": [str(member_ids[0])],
                }
            )
        raise AssertionError(f"schema bất ngờ: {name}")

    monkeypatch.setattr(nodes_mod, "chat_structured", fake_chat)
    return state


def _cleanup(planted: dict) -> None:
    """Dọn đúng row test vừa tạo — llm_call_logs TRƯỚC analysis_runs (FK)."""
    cid, mids = planted["cluster_id"], planted["member_ids"]
    with SessionLocal() as db:
        ins_ids = db.scalars(
            select(Insight.id).where(Insight.title.like(_TITLE_PREFIX + "%"))
        ).all()
        if ins_ids:
            db.execute(delete(ActionDraft).where(ActionDraft.insight_id.in_(ins_ids)))
            db.execute(
                delete(InsightReview).where(InsightReview.insight_id.in_(ins_ids))
            )
        db.execute(delete(Insight).where(Insight.title.like(_TITLE_PREFIX + "%")))

        run_id = planted.get("run_id")
        if run_id is not None:
            db.execute(
                text("DELETE FROM llm_call_logs WHERE analysis_run_id = :rid"),
                {"rid": str(run_id)},
            )
            run = db.get(AnalysisRun, run_id)
            if run is not None:
                db.delete(run)

        # FK order: feedbacks TRƯỚC analysis_runs (members trỏ qrun) — xóa
        # ngược thứ tự này là restrict → rollback để lại rác (đã xảy ra).
        for fid in mids:
            fb = db.get(Feedback, fid)
            if fb is not None:
                db.delete(fb)
        cl = db.get(Cluster, cid)
        if cl is not None:
            db.delete(cl)

        qrun_id = planted.get("qrun_id")
        if qrun_id is not None:
            qrow = db.get(AnalysisRun, qrun_id)
            if qrow is not None:
                db.delete(qrow)
        db.commit()

        left = _count_stray(db)
        assert left == 0, f"còn {left} row feedback agapi-* chưa dọn"


def test_full_trajectory_to_interrupt_then_approve(client: TestClient, planted) -> None:
    """Trajectory đầy đủ qua HTTP thật: runs → poll pending_approval → approve."""
    auth = _login(client)
    try:
        r = client.post("/api/agent/runs", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        run_id = body["run_id"]
        planted["run_id"] = run_id
        assert body["targets"] == [str(planted["cluster_id"])]

        # ---- Poll tới interrupt ----
        deadline = time.monotonic() + _POLL_SEC
        status_body: dict | None = None
        while time.monotonic() < deadline:
            rg = client.get(f"/api/agent/runs/{run_id}", headers=auth)
            assert rg.status_code == 200, rg.text
            status_body = rg.json()
            if status_body.get("pending_approval"):
                break
            if status_body.get("status") == "failed":
                pytest.fail(f"run failed sớm: {status_body.get('error')}")
            if status_body.get("status") == "completed":
                pytest.fail(
                    f"run completed MÀ không interrupt (critic drop cụm?): {status_body}"
                )
            time.sleep(_POLL_STEP)
        assert status_body and status_body["pending_approval"], (
            f"hết {_POLL_SEC}s chưa interrupt: {status_body}"
        )
        pa = status_body["pending_approval"]
        assert set(pa) >= {"insight", "quotes", "metrics", "precedents", "options"}
        assert pa["options"] == ["approve", "edit", "reject"]
        assert _TITLE_PREFIX in pa["insight"]["title"]
        joined = str(pa)
        assert "RAW-CONTENT-SEED" not in joined, "canary PII lộ vào payload!"

        # budget: fake chat KHÔNG ghi llm_call_logs → API đếm 0; đếm thật nằm ở
        # counter fixture (route×4 + generate_insight×1 = 5) — cả hai ≤ cap 24
        assert planted["llm_calls"] == 5, planted["llm_calls"]
        assert status_body["llm_calls_used"] <= status_body["llm_budget"]
        assert status_body["llm_calls_used"] == 0, "fake LLM không được ghi log"
        # steps_used chỉ đếm DISPATCH tool (nodes.dispatch) — script có đúng
        # 3 tool call (metrics/quotes/precedents); synthesize không tăng.
        assert status_body["steps_used"] == 3

        # ---- Approve qua API ----
        rd = client.post(
            f"/api/agent/runs/{run_id}/decision",
            json={"action": "approve", "reason": "đúng vấn đề"},
            headers=auth,
        )
        assert rd.status_code == 200, rd.text
        dec = rd.json()
        insight_id = uuid_mod.UUID(dec["insight_id"])
        assert dec["review_status"] == "approved"
        assert dec["drafts_created"] == 2

        # ---- Assert DB đúng 1 bộ ----
        with SessionLocal() as db:
            ins = db.get(Insight, insight_id)
            assert ins is not None
            assert ins.review_status.value == "approved"
            reviews = db.scalars(
                select(InsightReview).where(InsightReview.insight_id == insight_id)
            ).all()
            assert len(reviews) == 1, "InsightReview phải đúng 1 dòng"
            assert reviews[0].action.value == "approve"
            drafts = db.scalars(
                select(ActionDraft).where(ActionDraft.insight_id == insight_id)
            ).all()
            assert len(drafts) == 2, "draft_ticket + slack_message"

        # run completed sau resume
        rr = client.get(f"/api/agent/runs/{run_id}", headers=auth)
        assert rr.json()["status"] == "completed"
    finally:
        _cleanup(planted)


def test_decision_edit_without_fields_422(client: TestClient) -> None:
    """Validator schema: action=edit thiếu edited_* → 422 (không cần graph)."""
    auth = _login(client)
    r = client.post(
        "/api/agent/runs/00000000-0000-0000-0000-000000000000/decision",
        json={"action": "edit"},
        headers=auth,
    )
    assert r.status_code == 422


def test_unknown_run_404(client: TestClient) -> None:
    auth = _login(client)
    rid = "00000000-0000-0000-0000-000000000001"
    rg = client.get(f"/api/agent/runs/{rid}", headers=auth)
    assert rg.status_code == 404
    rp = client.post(
        f"/api/agent/runs/{rid}/decision",
        json={"action": "approve"},
        headers=auth,
    )
    assert rp.status_code == 404


def test_operations_role_allowed(client: TestClient) -> None:
    """operations cũng thuộc guard router (pm|operations) — 404 chứ không 403."""
    auth = _login(client, UserRole.operations)
    rg = client.get(
        "/api/agent/runs/00000000-0000-0000-0000-000000000002", headers=auth
    )
    assert rg.status_code == 404, "role đúng phải đi qua được router guard"

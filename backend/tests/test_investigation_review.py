"""Review receipt must not wait for an LLM continuation or lose retryability."""
import uuid

import pytest

from understand_agent import runner


def test_review_receipt_returns_before_graph_and_rejects_duplicate(monkeypatch):
    from understand_agent import review_tasks
    run_id = uuid.uuid4()
    queued = []
    monkeypatch.setattr(runner, "get_run_snapshot", lambda _: {"insight_id": "draft"})
    review_tasks.queue_review(run_id, {"action": "approve"}, lambda *args: queued.append(args))
    assert len(queued) == 1
    assert review_tasks.review_state(run_id)["processing"] is True
    with pytest.raises(ValueError):
        review_tasks.queue_review(run_id, {"action": "approve"}, lambda *args: queued.append(args))
    assert len(queued) == 1
    monkeypatch.setattr(runner, "resume_with_decision", lambda *_: {"final_status": "approved"})
    queued[0][0](*queued[0][1:])
    assert review_tasks.review_state(run_id)["processing"] is False


def test_failed_review_can_retry_without_reporting_approval(monkeypatch):
    from understand_agent import review_tasks
    run_id = uuid.uuid4()
    queued = []
    monkeypatch.setattr(runner, "get_run_snapshot", lambda _: {"insight_id": "draft"})
    def fail(*_):
        raise RuntimeError("checkpoint unavailable")
    monkeypatch.setattr(runner, "resume_with_decision", fail)
    review_tasks.queue_review(run_id, {"action": "approve"}, lambda *args: queued.append(args))
    queued[0][0](*queued[0][1:])
    state = review_tasks.review_state(run_id)
    assert state["processing"] is False
    assert state["error"]
    review_tasks.queue_review(run_id, {"action": "approve"}, lambda *args: queued.append(args))
    assert review_tasks.review_state(run_id)["processing"] is True
    monkeypatch.setattr(runner, "resume_with_decision", lambda *_: {})
    queued[-1][0](*queued[-1][1:])


def test_completed_thread_is_not_queued(monkeypatch):
    from understand_agent import review_tasks
    monkeypatch.setattr(runner, "get_run_snapshot", lambda _: None)
    with pytest.raises(ValueError):
        review_tasks.queue_review(uuid.uuid4(), {"action": "approve"}, lambda *_: pytest.fail("queued"))


def test_snapshot_cache_expires_on_invalidation(monkeypatch):
    calls = []
    run_id = uuid.uuid4()
    def read(_):
        calls.append(True)
        return {"insight_id": "pending"}
    monkeypatch.setattr(runner, "_load_run_snapshot", read)
    assert runner.get_run_snapshot(run_id)["insight_id"] == "pending"
    runner.get_run_snapshot(run_id)
    assert len(calls) == 1
    runner.invalidate_snapshot(run_id)
    runner.get_run_snapshot(run_id)
    assert len(calls) == 2


def test_background_route_receipt_preserves_authenticated_reviewer(monkeypatch):
    from types import SimpleNamespace
    from app.api.routes import agent
    from app.schemas.agent import AgentDecisionIn
    from understand_agent import review_tasks
    run_id, user_id = uuid.uuid4(), uuid.uuid4()
    seen = []
    from app.models.enums import RunStatus
    monkeypatch.setattr(agent, "_load_run", lambda *_: SimpleNamespace(id=run_id, status=RunStatus.running))
    monkeypatch.setattr(review_tasks, "queue_review", lambda rid, payload, enqueue: seen.append(payload))
    response = agent.decide_agent_run(run_id, AgentDecisionIn(action="approve"), background=True, db=None, user=SimpleNamespace(id=user_id))
    assert response.status_code == 202
    assert seen[0]["reviewer_id"] == str(user_id)
    assert b'"processing"' in response.body


def test_cluster_without_members_in_product_cannot_be_evidence():
    from types import SimpleNamespace
    from app.analytics.tools import inspect_cluster, InspectClusterInput
    class DB:
        def get(self, *_):
            return SimpleNamespace(id=uuid.uuid4())
        def scalar(self, *_):
            return 0
        def execute(self, *_):
            pytest.fail("must reject before reading cluster statistics")
    with pytest.raises(LookupError):
        inspect_cluster(DB(), uuid.uuid4(), InspectClusterInput(cluster_id=str(uuid.uuid4())))


def test_http_receipt_does_not_wait_for_continuation(monkeypatch):
    import threading
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes import agent
    from app.api.deps import get_current_user, get_db
    from app.models.enums import RunStatus
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def work(*_):
        entered.set()
        release.wait(2)
        finished.set()
        return {}
    monkeypatch.setattr(runner, "get_run_snapshot", lambda _: {"insight_id":"draft"})
    monkeypatch.setattr(runner, "resume_with_decision", work)
    run_id = uuid.uuid4()
    monkeypatch.setattr(agent, "_load_run", lambda *_: SimpleNamespace(id=run_id, status=RunStatus.running))
    api = FastAPI()
    api.include_router(agent.router)
    api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    api.dependency_overrides[get_db] = lambda: None
    try:
        with TestClient(api) as client:
            response = client.post(f"/api/agent/runs/{run_id}/decision?background=true", json={"action":"approve"})
            assert response.status_code == 202
            assert entered.wait(.5)
            assert not finished.is_set(), "HTTP receipt waited for the continuation"
    finally:
        release.set()
        finished.wait(2)

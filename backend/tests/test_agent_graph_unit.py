"""Graph-level unit test phase 19 Task 3 — InMemorySaver + fake LLM/executors,
KHÔNG đụng DB thật (SessionLocal/budget/membership bị patch).

Phủ đúng những gì plan yêu cầu chứng minh trước khi commit T2+T3 ("sau khi
route sống"): vòng route→dispatch→assess chạy được, budget cạn ép finish
không tốn router call, cap bước chặn ở _after_assess, và cơ chế
interrupt/resume trả đúng payload qua Command(resume=…).
"""

from __future__ import annotations

import uuid

import pytest
from langgraph.types import Command
from pydantic import BaseModel


# --- Fakes -------------------------------------------------------------------


class _MetricsOut(BaseModel):
    severity_dist: dict[str, int] = {}
    suggested_priority: float = 0.0
    is_emerging: bool = False
    is_spike: bool = False
    name: str = "cụm giả"
    summary: str = ""


class _QuotesOut(BaseModel):
    quotes: list[dict] = [{"feedback_id": "00000000-0000-0000-0000-000000000000"}]


class _PrecedentsOut(BaseModel):
    matches: list[dict] = [{"insight_id": "00000000-0000-0000-0000-000000000000"}]


class _DraftOut(BaseModel):
    title: str = "Tiêu đề giả"
    summary: str = "Tóm tắt giả."
    suggested_action: str = "Hành động giả."
    evidence_feedback_ids: list[uuid.UUID] = []


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def rollback(self):
        pass

    def get(self, *args, **kwargs):
        return None


@pytest.fixture()
def agent_env(monkeypatch):
    """Patch mọi seam DB của nodes — trả handle điều khiển kịch bản."""
    from happynest_agent import nodes

    calls: list[str] = []
    script: list[object] = []

    def fake_chat(system, user, schema, **kwargs):
        item = script.pop(0)
        calls.append(getattr(schema, "__name__", "?"))
        if isinstance(item, BaseModel):
            return item
        return schema.model_validate({"next": item, "rationale": "scripted"})

    member_id = uuid.uuid4()

    fake_executors = {
        "get_cluster_metrics": lambda db, params: _MetricsOut(),
        "fetch_evidence_quotes": lambda db, params: _QuotesOut(),
        "retrieve_similar_insights": lambda db, params: _PrecedentsOut(),
    }
    # input_model chỉ cần callable nhận kwargs; description cho prompt router
    fake_tools = {
        name: type("S", (), {"input_model": dict, "description": f"fake {name}"})
        for name in fake_executors
    }

    monkeypatch.setattr(nodes, "chat_structured", fake_chat)
    monkeypatch.setattr(nodes, "EXECUTORS_REG", fake_executors)
    monkeypatch.setattr(nodes, "TOOLS_REG", fake_tools)
    monkeypatch.setattr(nodes, "SessionLocal", _FakeSession)
    monkeypatch.setattr(nodes, "_budget_left", lambda db, run_id: 99)
    monkeypatch.setattr(nodes, "_cluster_members", lambda db, cid: [member_id])
    persist_calls: list[dict] = []

    def fake_persist(state):
        draft = dict(state["insight_draft"])
        draft["id"] = str(uuid.uuid4())
        persist_calls.append(draft)
        return {
            "insights_created": [uuid.UUID(draft["id"])],
            "risk_level": state.get("_forced_risk", "high"),
            "insight_draft": draft,
        }

    monkeypatch.setattr(nodes, "persist_insight", fake_persist)
    apply_calls: list[dict] = []

    def fake_apply(state):
        apply_calls.append(dict(state.get("decision") or {}))
        return {"decision": {**(state.get("decision") or {}), "done": True}}

    monkeypatch.setattr(nodes, "apply_decision", fake_apply)
    return {
        "nodes": nodes,
        "script": script,
        "calls": calls,
        "member_id": member_id,
        "persist_calls": persist_calls,
        "apply_calls": apply_calls,
    }


def _build():
    from langgraph.checkpoint.memory import InMemorySaver

    from happynest_agent.graph import build_agent_graph

    saver = InMemorySaver()
    return build_agent_graph(saver), saver


def _config(run_id: uuid.UUID) -> dict:
    return {"configurable": {"thread_id": f"agent-{run_id}"}}


# --- Scenarios ---------------------------------------------------------------


def test_route_loop_tools_then_finish(agent_env) -> None:
    """Kịch bản A: router chọn 2 tool rồi finish — vòng assess→route→dispatch
    tích lũy observations/evidence đúng, chạy tới END."""
    graph, _ = _build()
    env = agent_env
    env["script"].extend(["get_cluster_metrics", "fetch_evidence_quotes", "finish"])

    run_id = uuid.uuid4()
    t1 = uuid.uuid4()
    from happynest_agent.state import initial_state

    final = graph.invoke(initial_state(run_id, [t1]), _config(run_id))

    assert env["calls"] == ["RouteDecision"] * 3
    assert final["steps_used"] == 2, "chỉ 2 dispatch tốn step; finalize không"
    assert len(final["observations"]) == 3, "2 tool + 1 marker finalize"
    ev = final["evidence"][str(t1)]
    assert "metrics" in ev and "quotes" in ev
    assert final["insights_created"] == []


def test_budget_exhausted_finishes_without_router_call(agent_env) -> None:
    """Kịch bản B: ngân sách = 0 → route trả finish CỨNG, không gọi LLM."""
    graph, _ = _build()
    env = agent_env
    env["nodes"]._budget_left = lambda db, run_id: 0  # type: ignore[assignment]

    run_id = uuid.uuid4()
    from happynest_agent.state import initial_state

    final = graph.invoke(initial_state(run_id, [uuid.uuid4()]), _config(run_id))

    assert env["calls"] == [], "router không được tốn call nào"
    assert (final.get("route_decision") or {})["next"] == "finish"


def test_step_cap_goes_straight_to_synth_and_interrupt(agent_env) -> None:
    """Kịch bản C: steps_used đã ≥ cap + evidence đủ → _after_assess bỏ qua
    router, đi thẳng synthesize → critic pass → persist → risk high → interrupt.
    Resume bằng Command(resume) chạy tới END qua apply_decision."""
    graph, saver = _build()
    env = agent_env
    env["script"].append(_DraftOut(evidence_feedback_ids=[env["member_id"]]))

    run_id = uuid.uuid4()
    t1 = uuid.uuid4()
    from happynest_agent.state import initial_state

    state = initial_state(run_id, [t1])
    state["steps_used"] = 12  # == AGENT_MAX_STEPS mặc định
    state["evidence"] = {
        str(t1): {"metrics": {}, "quotes": [], "precedents": []}
    }

    config = _config(run_id)
    result = graph.invoke(state, config)

    assert env["calls"] == ["InsightDraft"], "không được tốn router call nào"
    assert "__interrupt__" in result, f"phải đậu ở interrupt, thấy: {result.keys()}"

    # thread_phase đọc snapshot phải báo interrupted kèm payload đầy đủ
    from happynest_agent.graph import snapshot_payload, thread_phase

    snap = graph.get_state(config)
    assert thread_phase(snap) == "interrupted"
    payload = snapshot_payload(snap)
    assert payload["options"] == ["approve", "edit", "reject"]
    assert payload["insight"]["title"]

    # resume → apply_decision nhận đúng payload reviewer gắn vào
    env["script"].clear()
    final = graph.invoke(
        Command(resume={"action": "approve", "reason": "ok"}), config
    )
    assert env["apply_calls"][-1]["action"] == "approve"
    assert final["decision"].get("done") is True

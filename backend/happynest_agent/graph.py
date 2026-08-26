"""Assembly StateGraph agent fully LLM-routed (phase 19 Task 3 Step 3.1).

Topology::

    START → assess ──(còn target & chưa quá cap)──→ route
      │                    │
      │ (hết target /      ├─ tool name ──→ dispatch ──→ assess (loop)
      │  quá cap mà thiếu  ├─ synthesize ──→ critic ─┬─(pass)──→ persist_insight
      │  evidence)         │                        ├─(None)──→ critic_recheck ─┬─(pass)→ persist
      ↓                    ↓                        └─(drop)──→ assess          └─(drop)→ assess
      finalize_no_insight → END                                                     │
                                                                                    ↓
                                              risk_gate ──(low)───→ auto_finalize ──→ assess
                                                        ──(high)──→ await_approval → apply_decision → END

Conditional edges là ĐIỂM THỰC THI biên an toàn: cap bước
AGENT_MAX_STEPS chặn ở ``_after_assess`` (trước khi tốn thêm 1 router call);
ngân sách LLM chặn trong node ``route`` (xem nodes.py).
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from happynest_agent import nodes
from happynest_agent.state import AgentState, initial_state


def _has_synth_evidence(state: AgentState) -> bool:
    """Cụm hiện tại đã đủ metrics + quotes để tổng hợp mà không cần tool nữa?"""
    bucket = state.get("evidence", {}).get(str(state.get("current_cluster")), {})
    return "metrics" in bucket and "quotes" in bucket


def _after_assess(state: AgentState) -> str:
    """Cap bước CHẶN Ở ĐÂY — trước route, tiết kiệm 1 router call khi quá cap."""
    if not state.get("current_cluster"):
        return "finalize_no_insight"  # hết target → đóng run
    from app.core.config import get_settings

    if state.get("steps_used", 0) >= get_settings().AGENT_MAX_STEPS:
        # quá cap: dùng nốt evidence có sẵn nếu đủ, không cho loop tool nữa
        return "synthesize" if _has_synth_evidence(state) else "finalize_no_insight"
    return "route"


def _after_route(state: AgentState) -> str:
    decision = state.get("route_decision") or {}
    nxt = decision.get("next")
    if nxt == "synthesize":
        return "synthesize"
    if nxt == "finish":
        return "finalize_no_insight"
    # tên tool (kể cả lạ — Literal Pydantic đã chặn phần lớn): dispatch tự xử
    # lý unknown thành obs lỗi rồi conditional đưa về assess
    return "dispatch"


def _after_critic(state: AgentState) -> str:
    result = state.get("critic_result")
    if result == "pass":
        return "persist_insight"
    if result == "drop":
        return "assess"  # cụm bị bỏ — sang target kế
    return "critic_recheck"  # None = vừa reflection xong, kiểm tra lần 2


def _after_recheck(state: AgentState) -> str:
    return "persist_insight" if state.get("critic_result") == "pass" else "assess"


def _after_risk_gate(state: AgentState) -> str:
    return "await_approval" if state.get("risk_level") == "high" else "auto_finalize"


def build_agent_graph(checkpointer):
    """Compile graph với checkpointer truyền vào (AsyncPostgresSaver prod /
    InMemorySaver unit test). Nodes đồng bộ — chạy được qua ainvoke (langgraph
    tự đẩy vào thread executor) đúng như hitl_graph."""

    builder = StateGraph(AgentState)
    builder.add_node("assess", nodes.assess)
    builder.add_node("route", nodes.route)
    builder.add_node("dispatch", nodes.dispatch)
    builder.add_node("synthesize", nodes.synthesize)
    builder.add_node("critic", nodes.critic)
    builder.add_node("critic_recheck", nodes.critic_recheck)
    builder.add_node("persist_insight", nodes.persist_insight)
    builder.add_node("risk_gate", nodes.risk_gate)
    builder.add_node("auto_finalize", nodes.auto_finalize)
    builder.add_node("await_approval", nodes.await_approval)
    builder.add_node("apply_decision", nodes.apply_decision)
    builder.add_node("finalize_no_insight", nodes.finalize_no_insight)

    builder.add_edge(START, "assess")
    builder.add_conditional_edges(
        "assess",
        _after_assess,
        ["route", "synthesize", "finalize_no_insight"],
    )
    builder.add_conditional_edges(
        "route",
        _after_route,
        ["dispatch", "synthesize", "finalize_no_insight"],
    )
    builder.add_conditional_edges("dispatch", lambda s: "assess", ["assess"])
    builder.add_edge("synthesize", "critic")
    builder.add_conditional_edges(
        "critic",
        _after_critic,
        ["persist_insight", "critic_recheck", "assess"],
    )
    builder.add_conditional_edges(
        "critic_recheck",
        _after_recheck,
        ["persist_insight", "assess"],
    )
    builder.add_edge("persist_insight", "risk_gate")
    builder.add_conditional_edges(
        "risk_gate",
        _after_risk_gate,
        ["auto_finalize", "await_approval"],
    )
    builder.add_conditional_edges("auto_finalize", lambda s: "assess", ["assess"])
    builder.add_edge("await_approval", "apply_decision")
    builder.add_edge("apply_decision", END)
    builder.add_edge("finalize_no_insight", END)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Phân loại trạng thái thread (mirror _next_graph_step của hitl_graph nhưng
# cho topology agent) — runner/routes đọc để quyết start | resume | continue |
# completed.
# ---------------------------------------------------------------------------


def pending_interrupts(snap) -> list:
    tasks = getattr(snap, "tasks", None) or ()
    interrupts: list = []
    for task in tasks:
        interrupts.extend(getattr(task, "interrupts", ()) or ())
    return interrupts


def thread_phase(snap) -> str:
    """start | interrupted | mid-flight | completed.

    - mid-flight: crash SAU khi interrupt đã tiêu thụ nhưng graph chưa hết —
      chạy nốt bằng ainvoke(None) không cần payload mới.
    """
    values = getattr(snap, "values", None) or {}
    nxt = list(getattr(snap, "next", None) or ())
    if not values:
        return "start"
    if pending_interrupts(snap):
        return "interrupted"
    if nxt:
        return "mid-flight"
    return "completed"


def snapshot_payload(snap) -> dict[str, Any]:
    """Interrupt payload đang đậu (cho GET /runs/{id}.pending_approval) — rỗng
    nếu thread không ở interrupt."""
    ints = pending_interrupts(snap)
    if not ints:
        return {}
    value = getattr(ints[0], "value", None)
    return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "build_agent_graph",
    "initial_state",
    "pending_interrupts",
    "snapshot_payload",
    "thread_phase",
]

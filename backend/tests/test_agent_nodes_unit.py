"""Unit test thuần nodes phase 19 Task 2 — KHÔNG đụng DB, KHÔNG gọi LLM.

Phủ các mảnh deterministic của graph: Literal chặn tên tool lạ (biên an toàn
plan §2), bảng rule risk gate, khuôn draft template, và invariant state schema
(guard chống drift giữa AgentState và initial_state — lỗi trùng hàm từng xảy ra
khi viết Task 2).
"""

import uuid

import pytest
from pydantic import ValidationError


def _run_id() -> uuid.UUID:
    return uuid.uuid4()


def test_nodes_module_imports_and_registry_built() -> None:
    """Import smoke — registry dựng lúc import phải đủ 5 tool."""
    from happynest_agent.nodes import EXECUTORS_REG, TOOLS_REG

    assert set(TOOLS_REG) == {
        "classify_batch",
        "embed_batch",
        "get_cluster_metrics",
        "fetch_evidence_quotes",
        "retrieve_similar_insights",
    }
    assert set(EXECUTORS_REG) == set(TOOLS_REG)


def test_route_decision_literal_blocks_unknown_tool() -> None:
    """Biên an toàn: router KHÔNG thể chọn tên ngoài registry/2 nhánh kết."""
    from happynest_agent.nodes import RouteDecision

    with pytest.raises(ValidationError):
        RouteDecision.model_validate(
            {"next": "delete_all_feedbacks", "rationale": "try to escape"}
        )
    with pytest.raises(ValidationError):
        RouteDecision.model_validate({"next": "", "rationale": "x"})
    # 2 nhánh kết vẫn hợp lệ
    for nxt in ("synthesize", "finish"):
        decision = RouteDecision.model_validate({"next": nxt, "rationale": "ok"})
        assert decision.next == nxt


def test_route_decision_rationale_capped() -> None:
    from happynest_agent.nodes import RouteDecision

    with pytest.raises(ValidationError):
        RouteDecision.model_validate(
            {"next": "finish", "rationale": "x" * 201}
        )


def test_escalate_rule_table() -> None:
    """Risk gate thuần rule plan §2.7: priority ≥ 0.70 OR share ≥ 0.30 OR
    (emerging AND spike) → high; còn lại low."""
    from happynest_agent.nodes import _escalate

    # priority vượt ngưỡng
    assert _escalate({"suggested_priority": 0.70}, share_hc=0.0) == "high"
    assert _escalate({"suggested_priority": 0.95}, share_hc=0.0) == "high"
    # priority dưới ngưỡng nhưng share high+critical vượt
    assert _escalate({"suggested_priority": 0.10}, share_hc=0.31) == "high"
    # emerging + spike đồng thời
    assert _escalate(
        {"suggested_priority": 0.10, "is_emerging": True, "is_spike": True},
        share_hc=0.0,
    ) == "high"
    # emerging mà không spike → low
    assert _escalate(
        {"suggested_priority": 0.10, "is_emerging": True, "is_spike": False},
        share_hc=0.0,
    ) == "low"
    # không tín hiệu nào / metrics rỗng → low
    assert _escalate({}, share_hc=0.0) == "low"
    # biên dưới ngưỡng: 0.69 < 0.70 và 0.29 < 0.30
    assert _escalate({"suggested_priority": 0.69}, share_hc=0.29) == "low"


def test_high_critical_share_counts_only_high_critical() -> None:
    from happynest_agent.nodes import _high_critical_share

    dist = {"critical": 1, "high": 1, "medium": 2, "low": 2}
    assert _high_critical_share({"severity_dist": dist}) == pytest.approx(2 / 6)
    assert _high_critical_share({"severity_dist": {}}) == 0.0
    assert _high_critical_share({}) == 0.0


def test_draft_templates_shape_and_kinds() -> None:
    """Auto path KHÔNG tốn LLM — khuôn fill cứng phải đủ ticket + slack."""
    from app.models.enums import DraftKind

    from happynest_agent.nodes import _draft_templates

    run_id = _run_id()
    templates = _draft_templates(run_id, "Lỗi đăng nhập", "Tăng đột biến", "Kiểm tra SSO")
    assert [t["kind"] for t in templates] == [
        DraftKind.draft_ticket.value,
        DraftKind.slack_message.value,
    ]
    joined = "\n".join(t["body"] for t in templates)
    assert "Lỗi đăng nhập" in joined
    assert str(run_id) in joined, "ticket phải mang run id để trace"


def test_initial_state_keys_match_schema() -> None:
    """Invariant: mọi key initial_state trả ra phải nằm trong AgentState và ĐỦ
    (guard regression — bản duplicate cũ từng shadow mất 3 key bổ sung)."""
    from happynest_agent.state import AgentState, initial_state

    state = initial_state(_run_id(), [_run_id()])
    annotations = set(AgentState.__annotations__)
    assert set(state.keys()) == annotations, (
        f"drift: thiếu={annotations - set(state)} thừa={set(state) - annotations}"
    )


def test_assess_picks_first_target_and_resets_signals() -> None:
    from happynest_agent.state import initial_state

    from happynest_agent.nodes import assess

    t1, t2 = _run_id(), _run_id()
    state = initial_state(_run_id(), [t1, t2])
    # mô phỏng tín hiệu sót từ cụm trước
    state.update(critic_result="pass", risk_level="high", current_cluster=t2)

    updates = assess(state)
    assert updates["current_cluster"] == t1
    assert updates["critic_result"] is None
    assert updates["risk_level"] is None


def test_pop_target_removes_current_and_resets() -> None:
    from happynest_agent.state import initial_state

    from happynest_agent.nodes import _pop_target

    t1, t2 = _run_id(), _run_id()
    state = initial_state(_run_id(), [t1, t2])
    state.update(current_cluster=t1)

    updates = _pop_target(state)
    assert updates["targets"] == [t2]
    assert updates["current_cluster"] is None
    assert updates["insight_draft"] is None
    assert updates["critic_failed_once"] is False


def test_obs_digest_tail_and_error_branch() -> None:
    from happynest_agent.state import initial_state

    from happynest_agent.nodes import _obs_digest

    state = initial_state(_run_id(), [])
    state["observations"] = [
        {"tool": f"tool_{i}", "output_summary": f"obs-{i}"} for i in range(8)
    ] + [{"tool": "bad_tool", "error": "boom"}]
    digest = _obs_digest(state)
    lines = digest.splitlines()
    assert len(lines) == 6, "digest chỉ giữ tail 6 obs"
    assert "tool_3" in lines[0]
    assert lines[-1].startswith("- bad_tool: boom")

"""Unit — planner UNDERSTAND dừng deterministic KHÔNG đốt plan call.

Bối cảnh 2026-10-23 (user report "loop plan→evaluate vô tận, chả ra gì"):
1. LangGraph default recursion_limit=25 chạm ngưỡng đúng lúc planner buộc
   synthesize ở vòng cuối → GraphRecursionError → run failed, không insight;
2. Stop conditions chỉ override SAU khi đã gọi LLM plan (lãng phí 1 call);
3. Evaluator xác nhận đủ bằng chứng nhưng planner LLM vẫn chọn tool mãi;
4. Planner chọn lại đúng tool+params vừa chạy → evidence lặp, không tiến triển.

Các test khóa điều kiện dừng ở tầng node — không cần DB/LLM thật (SessionLocal
+ chat_structured + get_settings đều monkeypatch).
"""

import uuid

import pytest

from understand_agent import nodes as nodes_mod
from understand_agent.nodes import PlannerOut, planner

_RUN_ID = str(uuid.uuid4())

_REPEAT_ACTION = {
    "action": "tool",
    "tool": "aggregate_feedback",
    "params": {"group_by": "topic"},
    "objective": "drill",
}


class _FakeDB:
    """Thay SessionLocal — scalar() trả số LLM call đã dùng (budget count)."""

    def __init__(self, used: int) -> None:
        self.used = used

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def scalar(self, *_args, **_kwargs):
        return self.used


class _StubSettings:
    UNDERSTAND_MAX_ITERATIONS = 3
    UNDERSTAND_LLM_BUDGET_PER_RUN = 10


@pytest.fixture()
def plan_spy(monkeypatch):
    calls = {"n": 0}

    def _fake(system, user, schema, **kwargs):
        calls["n"] += 1
        return PlannerOut.model_validate(_REPEAT_ACTION)

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    return calls


@pytest.fixture(autouse=True)
def stub_settings(monkeypatch):
    monkeypatch.setattr(nodes_mod, "get_settings", _StubSettings)


_EV = [{"evidence_id": "e0", "tool": "aggregate_feedback", "statement": "counts"}]


def _state(**over):
    base = {
        "run_id": _RUN_ID,
        "question": "which complaint matters most?",
        "product_context": {},
        "iteration": 0,
        "evaluations": [],
        "evidence": [],
        "tool_history": [],
    }
    base.update(over)
    return base


def test_max_iterations_stops_without_plan_call(plan_spy):
    out = planner(_state(iteration=3))
    assert out["next_action"]["action"] == "synthesize"
    assert out["next_action"]["objective"].startswith("Buộc tổng hợp")
    assert plan_spy["n"] == 0  # không tốn plan call


def test_budget_exhausted_stops_without_plan_call(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=10))
    out = planner(_state())
    assert out["next_action"]["action"] == "synthesize"
    assert plan_spy["n"] == 0


def test_two_consecutive_sufficient_stops_without_plan_call(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(
        _state(
            evaluations=[
                {"sufficient_evidence": True},
                {"sufficient_evidence": True},
            ]
        )
    )
    assert out["next_action"]["action"] == "synthesize"
    assert plan_spy["n"] == 0


def test_one_sufficient_still_asks_planner(monkeypatch, plan_spy):
    """1 lần đủ bằng chứng → planner vẫn được 1 nhịp drill-down nữa."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(_state(evidence=_EV, evaluations=[{"sufficient_evidence": True, "new_questions": ["vì sao?"]}]))
    assert plan_spy["n"] == 1
    assert out["next_action"]["action"] == "tool"


def test_insufficient_breaks_consecutive_count(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(
        _state(
            evidence=_EV,
            evaluations=[
                {"sufficient_evidence": True},
                {"sufficient_evidence": False},
                {"sufficient_evidence": True, "new_questions": ["vì sao?"]},
            ]
        )
    )
    assert plan_spy["n"] == 1
    assert out["next_action"]["action"] == "tool"


def test_repeat_same_tool_params_forces_synthesize(monkeypatch, plan_spy):
    """Planner chọn lại ĐÚNG tool+params bước vừa chạy → synthesize luôn."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(
        _state(
            evidence=_EV,
            tool_history=[
                {
                    "tool": "aggregate_feedback",
                    "ok": True,
                    "sig": nodes_mod._action_sig(_REPEAT_ACTION),
                }
            ]
        )
    )
    assert plan_spy["n"] == 1  # LLM có được hỏi, nhưng bị override
    assert out["next_action"]["action"] == "synthesize"


def test_different_params_still_allows_tool(monkeypatch, plan_spy):
    """Cùng tool khác params (drill-down hợp lệ) → cho chạy."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(
        _state(
            evidence=_EV,
            tool_history=[
                {
                    "tool": "aggregate_feedback",
                    "ok": True,
                    "sig": nodes_mod._action_sig(
                        {"tool": "aggregate_feedback", "params": {"group_by": "app_version"}}
                    ),
                }
            ]
        )
    )
    assert out["next_action"]["action"] == "tool"


def test_first_step_is_aggregate_first_without_llm(monkeypatch, plan_spy):
    """§69 aggregate-first là quy tắc cứng (owner 2026-11-05): chưa có evidence →
    aggregate theo field schema đầu tiên, KHÔNG hỏi LLM (trace E2E: qwen3 lọc hẹp
    ngay bước đầu và đếm thiếu)."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(
        _state(
            product_context={
                "schema_fields": [{"key": "app_version", "label": "App Version"}]
            }
        )
    )
    assert plan_spy["n"] == 0
    assert out["next_action"]["tool"] == "aggregate_feedback"
    assert out["next_action"]["params"] == {"group_by": "app_version"}


def test_first_step_prefers_topic_when_taxonomy_exists(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(_state(product_context={
        "schema_fields": [{"key": "app_version"}],
        "taxonomy": [{"slug": "ai_output_quality", "name": "AI Output Quality", "name_vi": None}],
    }))
    assert plan_spy["n"] == 0
    assert out["next_action"]["params"] == {"group_by": "topic"}


def test_no_evidence_no_schema_fields_opens_with_get_schema(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(_state(product_context={"schema_fields": []}))
    assert plan_spy["n"] == 0
    assert out["next_action"]["tool"] == "get_schema"
    assert out["next_action"]["params"] == {}


def test_with_evidence_llm_synthesize_is_allowed(monkeypatch):
    """Đã có evidence → LLM chọn synthesize thì tôn trọng (không ép tool)."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))

    def _fake(system, user, schema, **kwargs):
        return PlannerOut(action="synthesize", objective="enough")

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    out = planner(
        _state(
            evidence=[
                {
                    "evidence_id": str(uuid.uuid4()),
                    "tool": "aggregate_feedback",
                    "statement": "counts",
                }
            ]
        )
    )
    assert out["next_action"]["action"] == "synthesize"


def test_invalid_tool_with_evidence_wraps_up(monkeypatch):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))

    def _fake(system, user, schema, **kwargs):
        return PlannerOut.model_construct(
            action="tool", tool="tool_khong_ton_tai", params={}, objective="oops"
        )

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    out = planner(
        _state(
            evidence=[
                {
                    "evidence_id": str(uuid.uuid4()),
                    "tool": "aggregate_feedback",
                    "statement": "counts",
                }
            ]
        )
    )
    assert out["next_action"]["action"] == "synthesize"


def test_action_sig_canonical():
    """Sig không phụ thuộc thứ tự keys trong params."""
    a = nodes_mod._action_sig({"tool": "t", "params": {"a": 1, "b": 2}})
    b = nodes_mod._action_sig({"tool": "t", "params": {"b": 2, "a": 1}})
    assert a == b
    assert nodes_mod._action_sig(None) == ""


def test_non_adjacent_repeat_stops_cycle(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=2))
    out = planner(_state(evidence=_EV, tool_history=[
        {"sig": nodes_mod._action_sig(_REPEAT_ACTION)},
        {"sig": nodes_mod._action_sig({"tool": "get_schema", "params": {}})},
    ]))
    assert out["next_action"]["action"] == "synthesize"


def test_answered_question_stops_without_extra_planning(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=2))
    out = planner(_state(
        evidence=[{"evidence_id": "e", "tool": "aggregate_feedback", "statement": "counts"}],
        evaluations=[{"sufficient_evidence": True, "contradictions": [], "new_questions": []}],
    ))
    assert out["next_action"]["action"] == "synthesize"
    assert plan_spy["n"] == 0


def test_reserves_last_call_for_synthesis(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=9))
    out = planner(_state(llm_budget=10))
    assert out["next_action"]["action"] == "synthesize"
    assert plan_spy["n"] == 0


def test_followup_does_not_reuse_previous_sufficient_verdict(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=2))
    out = planner(_state(
        review_round_start=1,
        evidence=[{"evidence_id": "e", "tool": "get_schema", "statement": "schema"}],
        evaluations=[{"sufficient_evidence": True}],
    ))
    assert out["next_action"]["action"] == "tool"
    assert plan_spy["n"] == 1


def test_empty_filtered_lookup_tries_actual_product_samples(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=2))
    out = planner(_state(evidence=[{
        "evidence_id":"empty", "tool":"semantic_search", "statement":"no matches",
        "payload":{"matches":[]}, "ok":True,
    }]))
    assert out["next_action"]["tool"] == "representative_feedback"
    assert out["next_action"]["params"] == {}
    assert plan_spy["n"] == 0


# ------------------------------------------------ audit trace 2026-11-04


@pytest.mark.parametrize("raw, needle", [
    # thiếu params bắt buộc (trace thật: inspect_cluster không cluster_id)
    ({"action": "tool", "tool": "inspect_cluster", "params": {}, "objective": "x"}, "cluster_id"),
    # thiếu khóa tool, tên tool nằm trong objective
    ({"action": "tool", "params": {"cluster_id": str(uuid.uuid4())}, "objective": "inspect_cluster"},
     "bắt buộc có khóa 'tool'"),
    # tên tool méo
    ({"action": "tool", "tool": "aggregate_feedback, ", "params": {}, "objective": "x"}, "tool"),
])
def test_planner_out_rejects_trace_failure_modes(raw, needle):
    """Lỗi validate → fallback chain của chat_structured retry KÈM thông báo này."""
    with pytest.raises(ValueError) as exc:
        PlannerOut.model_validate(raw)
    assert needle in str(exc.value)


def test_planner_out_normalizes_params_and_strict_schema_requires_all_keys():
    out = PlannerOut.model_validate({"action": "tool", "tool": "compare_periods", "objective": "x",
                                     "params": {"current": "last_7_days", "previous": "previous_7_days"}})
    assert out.params == {"filters": {}, "current": "last_7_days", "previous": "previous_7_days"}
    schema = PlannerOut.strict_json_schema()
    assert set(schema["required"]) == {"action", "tool", "params", "objective"}
    assert "compare_periods" in schema["properties"]["tool"]["anyOf"][0]["enum"]


def test_temporal_question_measures_trend_before_stopping(monkeypatch, plan_spy):
    """'Vì sao tăng' + evaluator báo đủ 2 lần nhưng CHƯA đo xu hướng → compare_periods."""
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(_state(
        question="Vì sao phàn nàn về độ chính xác tăng trong tuần này?",
        evaluations=[{"sufficient_evidence": True}, {"sufficient_evidence": True}],
    ))
    assert out["next_action"]["tool"] == "compare_periods"
    assert out["next_action"]["params"]["current"] == "last_7_days"
    assert plan_spy["n"] == 0


def test_temporal_rule_runs_once(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    out = planner(_state(
        question="why did complaints rise?",
        evaluations=[{"sufficient_evidence": True}, {"sufficient_evidence": True}],
        tool_history=[{"tool": "compare_periods", "ok": True, "sig": "{}"}],
    ))
    assert out["next_action"]["action"] == "synthesize"


def test_temporal_llm_synthesize_reuses_last_filters(monkeypatch):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=0))
    monkeypatch.setattr(nodes_mod, "chat_structured",
                        lambda *a, **k: PlannerOut(action="synthesize", objective="enough"))
    prior = {"tool": "segment_feedback", "params": {"filters": {"ai_issue": "inaccuracy"}, "dimensions": ["source"]}}
    out = planner(_state(
        question="why did accuracy complaints rise?",
        evidence=[{"evidence_id": "e1", "tool": "segment_feedback", "statement": "seg"}],
        tool_history=[{"tool": "segment_feedback", "ok": True, "sig": nodes_mod._action_sig(prior)}],
    ))
    assert out["next_action"]["tool"] == "compare_periods"
    assert out["next_action"]["params"]["filters"] == {"ai_issue": "inaccuracy"}


def test_temporal_rule_respects_budget(monkeypatch, plan_spy):
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=8))  # budget 10 → còn 2 > ngưỡng stop? used>=9 mới stop
    out = planner(_state(
        question="why did complaints rise?",
        evaluations=[{"sufficient_evidence": True}, {"sufficient_evidence": True}],
    ))
    # còn đúng 2 call → vẫn đủ cho evaluate + synthesize
    assert out["next_action"]["tool"] == "compare_periods"
    monkeypatch.setattr(nodes_mod, "SessionLocal", lambda: _FakeDB(used=9))
    out = planner(_state(question="why did complaints rise?", evidence=_EV))
    assert out["next_action"]["action"] == "synthesize"

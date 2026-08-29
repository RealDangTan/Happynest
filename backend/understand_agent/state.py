"""UnderstandState — TypedDict graph state (VoC OS §25).

Nguyên tắc giữ từ graph cũ: state giữ RAW (JSON-serializable), node tự format
prompt của mình. evidence là list accumulate (Annotated add) — mỗi entry
{evidence_id, tool, statement, payload, coverage}.
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


def _add_list(left: list | None, right: list | None) -> list:
    return list(left or []) + list(right or [])


class UnderstandState(TypedDict, total=False):
    run_id: str
    product_id: str
    #: Câu hỏi user HOẶC mô tả system signal (spike/emerging)
    question: str
    trigger_type: str  # user_question | system_signal

    product_context: dict[str, Any]

    #: Tích lũy qua các vòng tool-loop (Annotated add)
    evidence: Annotated[list[dict[str, Any]], _add_list]
    evaluations: Annotated[list[dict[str, Any]], _add_list]
    tool_history: Annotated[list[str], _add_list]

    iteration: int
    llm_budget: int

    #: planner output hiện hành {action, tool?, params?, objective?}
    next_action: dict[str, Any] | None

    draft_insight: dict[str, Any] | None
    #: {action, edited_*?, reason?} từ Command(resume=…) — Gate #2
    decision: dict[str, Any] | None
    final_status: str
    insights_created: Annotated[list[str], _add_list]

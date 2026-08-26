"""AgentState — state schema của StateGraph fully LLM-routed (phase 19 Task 1).

Nguyên tắc LangGraph "keep state raw": chỉ dữ liệu thô — mỗi node tự format
prompt của mình. `observations` tích lũy qua các bước dispatch nên khai báo
Annotated[list, operator.add]; phần còn lại là replace-per-node.
"""

from __future__ import annotations

import operator
import uuid
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    run_id: uuid.UUID
    # cluster ids sẽ điều tra (top AGENT_TOP_CLUSTERS theo suggested_priority)
    targets: list[uuid.UUID]
    current_cluster: uuid.UUID | None
    # mỗi obs: {tool, input_tóm_tắt, output_tóm_tắt ≤500 ký tự} hoặc {tool, error}
    observations: Annotated[list[dict[str, Any]], operator.add]
    # evidence theo cluster: {cluster_id_str: {"metrics":…, "quotes":[…], "precedents":[…]}}
    evidence: dict[str, dict[str, Any]]
    insight_draft: dict[str, Any] | None
    critic_failed_once: bool
    risk_level: str | None  # "high" | "low" | None (risk_gate set)
    steps_used: int
    # resume payload từ POST /runs/{id}/decision: {action, edited_*?, reason?}
    decision: dict[str, Any] | None
    # --- bổ sung khi thực thi Task 2 so với danh sách plan §3.1.2 (đủ để
    # conditional edges đọc được tín hiệu giữa các node) ---
    route_decision: dict[str, Any] | None   # output node route: {next, rationale}
    critic_result: str | None               # "pass" | "drop"
    insights_created: Annotated[list[uuid.UUID], operator.add]  # insight ids đã persist


def initial_state(run_id: uuid.UUID, targets: list[uuid.UUID]) -> AgentState:
    """State khởi đầu cho 1 agent run — duy nhất điểm tạo state để test ghim."""
    return AgentState(
        run_id=run_id,
        targets=list(targets),
        current_cluster=None,
        observations=[],
        evidence={},
        insight_draft=None,
        critic_failed_once=False,
        risk_level=None,
        steps_used=0,
        decision=None,
        route_decision=None,
        critic_result=None,
        insights_created=[],
    )

"""UNDERSTAND graph — VoC OS §60 (plan 25 Task 2).

load_context → planner →{tool}→ dispatch → evaluator → planner (loop)
planner →{synthesize}→ synthesizer → persist_insight [INTERRUPT Gate #2]
→ apply_decision →{investigate_more}→ planner | END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from understand_agent import nodes
from understand_agent.state import UnderstandState


def build_graph(checkpointer):
    builder = StateGraph(UnderstandState)

    builder.add_node("load_context", nodes.load_context)
    builder.add_node("planner", nodes.planner)
    builder.add_node("dispatch", nodes.dispatch)
    builder.add_node("evaluator", nodes.evaluator)
    builder.add_node("synthesizer", nodes.synthesizer)
    builder.add_node("persist_insight", nodes.persist_insight)
    builder.add_node("apply_decision", nodes.apply_decision)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "planner")
    builder.add_conditional_edges(
        "planner",
        lambda s: "dispatch" if (s.get("next_action") or {}).get("action") == "tool" else "synthesizer",
        {"dispatch": "dispatch", "synthesizer": "synthesizer"},
    )
    builder.add_edge("dispatch", "evaluator")
    builder.add_edge("evaluator", "planner")
    builder.add_edge("synthesizer", "persist_insight")
    builder.add_edge("persist_insight", "apply_decision")
    builder.add_conditional_edges(
        "apply_decision",
        lambda s: "planner" if s.get("final_status") == "investigating" else END,
        {"planner": "planner", END: END},
    )
    return builder.compile(checkpointer=checkpointer)

"""Toolbox package — 5 tool deterministic sau lưng router (phase 18).

Registry đóng dần theo task: Task 6 assert đủ 5 tên hợp đồng:
classify_batch, embed_batch, get_cluster_metrics, fetch_evidence_quotes,
retrieve_similar_insights.
"""

from __future__ import annotations

from happynest_agent.tools.base import TOOLS, ToolInput, ToolSpec

__all__ = ["TOOLS", "ToolInput", "ToolSpec", "_build_registry"]


def _build_registry() -> dict[str, ToolSpec]:
    """Gom ToolSpec từ các module con đã có mặt (partial khi đang xây)."""
    registry: dict[str, ToolSpec] = {}
    try:
        from happynest_agent.tools.classify_batch import SPEC

        registry[SPEC.name] = SPEC
    except ImportError:  # module chưa viết — Task 2
        pass
    try:
        from happynest_agent.tools.embed_batch import SPEC

        registry[SPEC.name] = SPEC
    except ImportError:  # Task 2
        pass
    try:
        from happynest_agent.tools.metrics import SPEC

        registry[SPEC.name] = SPEC
    except ImportError:  # Task 3
        pass
    try:
        from happynest_agent.tools.evidence import SPEC

        registry[SPEC.name] = SPEC
    except ImportError:  # Task 4
        pass
    try:
        from happynest_agent.tools.precedents import SPEC

        registry[SPEC.name] = SPEC
    except ImportError:  # Task 5
        pass
    return registry

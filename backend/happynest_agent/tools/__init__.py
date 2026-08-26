"""Toolbox package — 5 tool deterministic sau lưng router (phase 18).

Registry đóng dần theo task: Task 6 assert đủ 5 tên hợp đồng:
classify_batch, embed_batch, get_cluster_metrics, fetch_evidence_quotes,
retrieve_similar_insights.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from happynest_agent.tools.base import TOOLS, ToolInput, ToolSpec

__all__ = ["EXECUTORS", "TOOLS", "ToolInput", "ToolSpec", "_build_registry"]


def _build_executors() -> dict[str, Callable[[Session, Any], Any]]:
    """Map tên tool → hàm execute(db, params). Dispatch phase 19 tra bảng này;
    tách khỏi ToolSpec để spec giữ thuần metadata (test không đụng DB)."""
    executors: dict[str, Callable[[Session, Any], Any]] = {}
    for mod_name in (
        "classify_batch",
        "embed_batch",
        "metrics",
        "evidence",
        "precedents",
    ):
        try:
            module = __import__(
                f"happynest_agent.tools.{mod_name}", fromlist=["execute"]
            )
            spec = getattr(module, "SPEC", None)
            execute = getattr(module, "execute", None)
            if spec is not None and execute is not None:
                executors[spec.name] = execute
        except ImportError:  # module chưa viết — partial khi đang xây
            pass
    return executors


def EXECUTORS() -> dict[str, Callable[[Session, Any], Any]]:
    return _build_executors()


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

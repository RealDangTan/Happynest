"""Smoke test khung registry — phase 18 Task 1 Step 1.2."""

import pytest


def test_registry_imports_and_returns_dict() -> None:
    from happynest_agent.tools import TOOLS
    from happynest_agent.tools.base import ToolInput, ToolSpec

    registry = TOOLS()
    assert isinstance(registry, dict)
    # mọi spec hiện có phải đúng hợp đồng + input kế thừa run_id base
    for name, spec in registry.items():
        assert spec.name == name
        assert len(spec.description.split()) > 3, "description phải là câu tiếng Anh tường minh"
        assert issubclass(spec.input_model, ToolInput), "input bắt buộc có run_id"


def test_tool_input_requires_run_id() -> None:
    from happynest_agent.tools.base import ToolInput

    with pytest.raises(ValueError):
        ToolInput()  # thiếu run_id


def test_package_layout_single_home() -> None:
    """Owner directive: code agent chỉ nằm ở happynest_agent (decisions 2026-08-26)."""
    import happynest_agent

    assert happynest_agent.__file__ is not None
    assert "happynest_agent" in happynest_agent.__file__.replace("\\", "/")


def test_registry_closes_all_five_tools() -> None:
    """Task 6 — tên chuỗi là HỢP ĐỒNG với router phase 19; đổi tên = sửa phase 19."""
    from happynest_agent.tools import TOOLS

    assert set(TOOLS()) == {
        "classify_batch",
        "embed_batch",
        "get_cluster_metrics",
        "fetch_evidence_quotes",
        "retrieve_similar_insights",
    }
    for spec in TOOLS().values():
        # output_model phải là BaseModel subclass — dispatch phase 19 validate
        # kết quả tool qua model này trước khi đưa vào state
        assert hasattr(spec.output_model, "model_validate")

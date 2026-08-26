"""Hợp đồng tool cho agent router — phase 18 Task 1 (plan 18-agent-toolbox.md).

Router phase 19 đọc `description` (1 câu tiếng Anh) để chọn tool nên chữ ở đó
LÀ HỢP ĐỒNG: đổi tên tool = phải sửa cả RouteDecision Literal bên graph.
Mọi input schema bắt buộc kế thừa `ToolInput` để có `run_id` passthrough vào
llm_call_logs khi tool chạm LLM.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base input cho mọi tool — bắt buộc có run_id để trace theo run."""

    run_id: uuid.UUID


class ToolSpec(BaseModel):
    name: str
    description: str  # 1 câu tiếng Anh — router sẽ đọc description này để chọn
    input_model: type[BaseModel]
    output_model: type[BaseModel]


def TOOLS() -> dict[str, ToolSpec]:
    """Registry gom từ 5 module con — đóng đủ 5 tên ở Task 6."""
    from happynest_agent.tools import _build_registry

    return _build_registry()

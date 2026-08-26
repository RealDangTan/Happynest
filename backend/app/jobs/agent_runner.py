"""Agent runner — orchestration DB quanh graph router (phase 19 Task 3 Step 3.2).

Trách nhiệm:
- chọn targets (TOP ``AGENT_TOP_CLUSTERS`` cụm có tín hiệu: emerging OR spike
  OR suggested_priority ≥ ngưỡng risk);
- INSERT AnalysisRun(pipeline_version="agent-router-v1") snapshot config;
- chạy graph trong BACKGROUND THREAD qua selector loop riêng (Windows quirk S5
  — async psycopg không chạy trên ProactorEventLoop; pattern y hệt hitl_graph
  nhưng ở đây thread nền vì run dài nhiều phút, không giữ request);
- on-complete/crash cập nhật status/error và NUỐT exception (triết lý
  BackgroundTasks phase 09: job chết không được nổ process).

Khác runner deterministic (analysis_runner): agent run KHÔNG replace-all —
insight mới insert thêm, không xoá insight cũ; tạo run mới khi run cũ đang
chạy là hành vi hợp lệ (ghi rõ trong api-checklist phase 19).
"""

from __future__ import annotations

import asyncio
import logging
import selectors
import threading
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.cluster import Cluster
from app.models.enums import RunStatus

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "agent-router-v1"

_ERROR_SUMMARY_MAX = 2000


def select_targets(db: Session) -> list[uuid.UUID]:
    """TOP N cụm đáng điều tra nhất — trần cứng AGENT_TOP_CLUSTERS."""
    s = get_settings()
    rows = db.scalars(
        select(Cluster.id)
        .where(
            Cluster.is_emerging.is_(True)
            | Cluster.is_spike.is_(True)
            | (Cluster.suggested_priority >= s.AGENT_RISK_PRIORITY_THRESHOLD)
        )
        .order_by(Cluster.suggested_priority.desc().nulls_last())
        .limit(s.AGENT_TOP_CLUSTERS)
    ).all()
    return list(rows)


# ---------------------------------------------------------------------------
# Event-loop plumbing (S5) — mirror hitl_graph
# ---------------------------------------------------------------------------


def _run_on_selector_loop(coro_fn):
    import asyncio as _asyncio

    return _asyncio.run(
        coro_fn(),
        loop_factory=lambda: _asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )


def _conn_string() -> str:
    """psycopg URI thuần cho AsyncPostgresSaver — bỏ prefix dialect SQLAlchemy."""
    return get_settings().database_url_sqla.replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def ensure_checkpointer_ready() -> bool:
    """Re-export mỏng của hitl_graph.setup — cùng 4 bảng checkpoint, setup
    đúng một lần mỗi process (đã gọi từ lifespan)."""
    from app.services.hitl_graph import ensure_checkpointer_ready as _ensure

    return _ensure()


class CheckpointUnavailable(Exception):
    """Saver không dựng được bảng checkpoint — route chuyển 503."""


# ---------------------------------------------------------------------------
# Graph execution flows
# ---------------------------------------------------------------------------


def _flow_start(run_id: uuid.UUID, targets: list[uuid.UUID]) -> dict[str, Any]:
    """Lần đầu chạy graph tới interrupt hoặc completed."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from happynest_agent.graph import build_agent_graph, initial_state

    async def _coro() -> dict[str, Any]:
        config = {"configurable": {"thread_id": f"agent-{run_id}"}}
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_agent_graph(saver)
            final = await graph.ainvoke(initial_state(run_id, targets), config)
            return dict(final)

    return _run_on_selector_loop(_coro)


def _flow_resume(run_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    """Resume thread đang đậu ở interrupt bằng Command(resume=payload)."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.types import Command

    from happynest_agent.graph import build_agent_graph

    async def _coro() -> dict[str, Any]:
        config = {"configurable": {"thread_id": f"agent-{run_id}"}}
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_agent_graph(saver)
            final = await graph.ainvoke(Command(resume=dict(payload)), config)
            return dict(final)

    return _run_on_selector_loop(_coro)


def _flow_continue(run_id: uuid.UUID) -> dict[str, Any]:
    """Crash giữa chừng SAU interrupt (resume_payload đã nằm checkpoint) —
    chạy nốt graph không cần payload mới."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from happynest_agent.graph import build_agent_graph

    async def _coro() -> dict[str, Any]:
        config = {"configurable": {"thread_id": f"agent-{run_id}"}}
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_agent_graph(saver)
            final = await graph.ainvoke(None, config)
            return dict(final)

    return _run_on_selector_loop(_coro)


def get_thread_state(run_id: uuid.UUID):
    """Snapshot state thread (aget_state) để route đọc pending_approval /
    phân loại resume. Raise CheckpointUnavailable nếu saver chưa sẵn sàng."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from happynest_agent.graph import build_agent_graph

    if not ensure_checkpointer_ready():
        raise CheckpointUnavailable("Bảng checkpoint LangGraph chưa dựng được.")

    async def _coro():
        config = {"configurable": {"thread_id": f"agent-{run_id}"}}
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_agent_graph(saver)
            return await graph.aget_state(config)

    return _run_on_selector_loop(_coro)


# ---------------------------------------------------------------------------
# Background-thread job + public API
# ---------------------------------------------------------------------------


def _mark_completed(run_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        if run is None or run.status == RunStatus.completed:
            return
        run.status = RunStatus.completed
        from datetime import datetime, timezone

        run.completed_at = datetime.now(timezone.utc)
        db.commit()


def _mark_failed(run_id: uuid.UUID, exc: Exception) -> None:
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            return
        from datetime import datetime, timezone

        run.status = RunStatus.failed
        run.error = f"{type(exc).__name__}: {exc}"[:_ERROR_SUMMARY_MAX]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()


def _execute_in_thread(run_id: uuid.UUID, targets: list[uuid.UUID]) -> None:
    """Thân thread nền — NUỐT mọi exception sau khi ghi vào row run."""
    try:
        logger.info("agent run %s bắt đầu với %d target.", run_id, len(targets))
        _flow_start(run_id, targets)
        _mark_completed(run_id)
        logger.info("agent run %s hoàn tất.", run_id)
    except Exception as exc:  # noqa: BLE001 — job chết không nổ process
        logger.exception("agent run %s crashed:", run_id)
        _mark_failed(run_id, exc)


def start_agent_run(db: Session) -> AnalysisRun:
    """Tạo row run + spawn thread nền; trả row NGAY (caller serialize ra response).

    Targets rỗng → vẫn tạo run nhưng completed ngay với note trong error
    (plan §3.2: 'rỗng → run completed ngay với note') — client thấy kết quả
    dứt khoát thay vì poll vô vọng.
    """
    settings = get_settings()
    targets = select_targets(db)
    run = AnalysisRun(
        pipeline_version=PIPELINE_VERSION,
        llm_model=settings.LLM_MODEL,
        prompt_version=settings.PROMPT_VERSION,
        embedding_model=settings.EMBEDDING_MODEL,
        total_count=len(targets),
    )
    if not targets:
        from datetime import datetime, timezone

        run.status = RunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.error = (
            "note: không có cụm nào đạt tín hiệu điều tra "
            "(emerging/spike/priority ≥ ngưỡng) — không sinh insight."
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    db.add(run)
    db.commit()
    db.refresh(run)
    threading.Thread(
        target=_execute_in_thread,
        args=(run.id, targets),
        name=f"agent-run-{run.id}",
        daemon=True,
    ).start()
    return run


def resume_with_decision(
    run_id: uuid.UUID, payload: dict[str, Any], *, reviewer_id: uuid.UUID
) -> dict[str, Any]:
    """POST /runs/{id}/decision — phân loại trạng thái thread rồi resume.

    - interrupted → Command(resume=payload+reviewer_id);
    - mid-flight (crash-dở-dâng sau interrupt) → chạy nốt ainvoke(None), KHÔNG
      nhận payload mới (mirror pre-check thu hẹp phase 13);
    - completed → raise ReviewAlreadyCompleted (route chuyển 409);
    - start → raise LookupError (run chưa từng vào graph — lỗi caller).
    """
    from app.services.hitl_graph import ReviewAlreadyCompleted

    from happynest_agent.graph import thread_phase

    if not ensure_checkpointer_ready():
        raise CheckpointUnavailable("Bảng checkpoint LangGraph chưa dựng được.")

    snap = get_thread_state(run_id)
    phase = thread_phase(snap)
    if phase == "completed":
        raise ReviewAlreadyCompleted(f"Agent run {run_id} đã hoàn tất.")
    if phase == "start":
        raise LookupError(f"Agent run {run_id} chưa từng khởi động graph.")

    if phase == "interrupted":
        # reviewer_id gắn vào payload ngay tại đây — node apply_decision đọc
        # state, không tin payload client tự khai tác giả.
        return _flow_resume(run_id, {**payload, "reviewer_id": str(reviewer_id)})
    return _flow_continue(run_id)

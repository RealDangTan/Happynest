"""UNDERSTAND runner — orchestration quanh graph (plan 25 Task 3).

Kế thừa pattern agent_runner cũ (strip 2026-08-28) + quirks S5 (decisions
2026-08-24): graph I/O chạy trên SelectorEventLoop RIÊNG qua
graph_runtime.run_on_selector_loop; connection psycopg bám loop nơi tạo —
mỗi thao tác mở saver riêng. Background daemon thread qua BackgroundTasks.
"""

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.services.graph_runtime import (
    CheckpointUnavailable,
    _conn_string,
    ensure_checkpointer_ready,
    pending_interrupts,
    run_on_selector_loop,
)
from understand_agent.graph import build_graph

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "understand-v1"


def start_understand_run(
    db, product_id: uuid.UUID, question: str, trigger_type: str = "user_question"
) -> AnalysisRun:
    """Tạo AnalysisRun + spawn graph run trong background thread. Trả run NGAY.

    Caller commit run row; thread tự chạy graph trên selector loop riêng.
    """
    settings = get_settings()
    run = AnalysisRun(
        pipeline_version=PIPELINE_VERSION,
        llm_model=settings.LLM_MODEL,
        prompt_version="understand-v1",
        embedding_model=settings.EMBEDDING_MODEL,
        total_count=1,  # 1 investigation per run
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    def _bg():
        try:
            submit_or_start(
                run.id,
                product_id,
                {"question": question, "trigger_type": trigger_type},
            )
        except Exception:  # noqa: BLE001 — background thread không được nổ process
            logger.exception("understand run %s crashed", run.id)
            with SessionLocal() as s:
                r = s.get(AnalysisRun, run.id)
                if r is not None and r.status == RunStatus.running:
                    r.status = RunStatus.failed
                    r.error = "understand graph crashed (see log)"
                    r.completed_at = datetime.now(timezone.utc)
                    s.commit()

    threading.Thread(target=_bg, name=f"understand-{run.id}", daemon=True).start()
    return run


def _thread_config(run_id: uuid.UUID) -> dict:
    return {"configurable": {"thread_id": f"understand-{run_id}"}}


def _run_graph(start_payload: dict | None, run_id: uuid.UUID, product_id: uuid.UUID) -> dict:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.types import Command

    async def _flow() -> dict:
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_graph(saver)
            config = _thread_config(run_id)
            if start_payload is not None:
                await graph.ainvoke(
                    {
                        "run_id": str(run_id),
                        "product_id": str(product_id),
                        "question": start_payload.get("question", ""),
                        "trigger_type": start_payload.get("trigger_type", "user_question"),
                        "llm_budget": get_settings().UNDERSTAND_LLM_BUDGET_PER_RUN,
                    },
                    config,
                )
            else:
                await graph.ainvoke(None, config)
            snap = await graph.aget_state(config)
            return dict(snap.values or {})

    return run_on_selector_loop(_flow)


def submit_or_start(
    run_id: uuid.UUID, product_id: uuid.UUID, start_payload: dict | None
) -> dict[str, Any]:
    """Chạy graph tới interrupt (lần đầu) hoặc chạy nốt (crash-mid-flight heal)."""
    if not ensure_checkpointer_ready():
        raise CheckpointUnavailable(
            "Không kết nối được Supabase để dựng bảng checkpoint LangGraph."
        )
    return _run_graph(start_payload, run_id, product_id)


def resume_with_decision(run_id: uuid.UUID, payload: dict) -> dict:
    """Gate #2 resume — classify thread phase (start/resume/continue/completed).

    Kế thừa pattern hitl_graph cũ: phase 'start' (thread chưa tồn tại — không
    hợp lệ cho decision), 'resume' (đang interrupt), 'continue' (crash sau
    interrupt — chạy nốt), 'completed' (409).
    """
    if not ensure_checkpointer_ready():
        raise CheckpointUnavailable("Checkpoint saver chưa sẵn sàng.")

    async def _flow() -> dict:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.types import Command

        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_graph(saver)
            config = _thread_config(run_id)
            snap = await graph.aget_state(config)
            values = dict(snap.values or {})
            nxt = list(snap.next or ())
            if not values:
                raise LookupError("Thread chưa tồn tại — start run trước.")
            if pending_interrupts(snap) or nxt == ["persist_insight"]:
                # ainvoke trả final state DICT (không phải snapshot) — không .values
                final = await graph.ainvoke(Command(resume=dict(payload)), config)
                return dict(final or {})
            if nxt:
                # crash-mid-flight: decision đã nằm trong checkpoint → chạy nốt
                final = await graph.ainvoke(None, config)
                return dict(final or {})
            raise RuntimeError("Thread understand đã hoàn tất — decision bị trùng.")

    return run_on_selector_loop(_flow)


def get_run_snapshot(run_id: uuid.UUID) -> dict | None:
    """Interrupt payload (Gate #2) nếu graph đang đậu chờ human; None nếu không."""
    if not ensure_checkpointer_ready():
        return None

    async def _flow():
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            graph = build_graph(saver)
            snap = await graph.aget_state(_thread_config(run_id))
            if not (dict(snap.values or {})):
                return None
            tasks = getattr(snap, "tasks", None) or ()
            for task in tasks:
                for intr in getattr(task, "interrupts", ()) or ():
                    return intr.value
            return None

    try:
        return run_on_selector_loop(_flow)
    except Exception:  # noqa: BLE001 — GET status không được nổ
        logger.exception("get_run_snapshot fail")
        return None

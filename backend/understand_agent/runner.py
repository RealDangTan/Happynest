"""UNDERSTAND runner — orchestration quanh graph (plan 25 Task 3).

Kế thừa pattern agent_runner cũ (strip 2026-08-28) + quirks S5 (decisions
2026-08-24): graph I/O chạy trên SelectorEventLoop RIÊNG qua
graph_runtime.run_on_selector_loop; connection psycopg bám loop nơi tạo —
mỗi thao tác mở saver riêng. Background daemon thread qua BackgroundTasks.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.observability import observe_pipeline
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
        product_id=product_id,  # isolation 0018 — route scope theo owner
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


def mark_stale_running_failed(max_age_minutes: int = 30) -> int:
    """Heal-on-startup: run 'running' quá hạn → failed.

    Thread nền graph là daemon — chết theo process khi server restart
    (--reload/dev) mà không ai đánh dấu run; để lại run 'running' vĩnh viễn
    khiến FE polling vô hạn. Chạy 1 lần lúc boot.

    Run đã tạo Insight (đậu Gate #2, chờ human decision) cũng status=running
    nhưng là TRẠNG THÁI HỢP LỆ — chỉ heal run CHƯA có insight nào.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    with SessionLocal() as db:
        from app.models.insight import Insight

        stale_ids = db.scalars(
            select(AnalysisRun.id).where(
                AnalysisRun.status == RunStatus.running,
                AnalysisRun.started_at < cutoff,
                ~select(Insight.id)
                .where(Insight.run_id == AnalysisRun.id)
                .exists(),
            )
        ).all()
        if not stale_ids:
            return 0
        now = datetime.now(timezone.utc)
        for row in db.scalars(
            select(AnalysisRun).where(AnalysisRun.id.in_(stale_ids))
        ).all():
            row.status = RunStatus.failed
            row.error = (
                f"stale running quá {max_age_minutes} phút — server restart "
                "giữa chừng? (heal-on-startup)"
            )
            row.completed_at = now
        db.commit()
        return len(stale_ids)


def _thread_config(run_id: uuid.UUID) -> dict:
    return {"configurable": {"thread_id": f"understand-{run_id}"}}


@observe_pipeline("understand")
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
    if start_payload is not None:
        from app.services.presidio_service import sanitize

        start_payload = dict(start_payload)
        start_payload["question"] = sanitize(str(start_payload.get("question", ""))).sanitized_text
    return _run_graph(start_payload, run_id, product_id)


@observe_pipeline("understand")
def resume_with_decision(run_id: uuid.UUID, payload: dict) -> dict:
    """Gate #2 resume — classify thread phase (start/resume/continue/completed).

    Kế thừa pattern hitl_graph cũ: phase 'start' (thread chưa tồn tại — không
    hợp lệ cho decision), 'resume' (đang interrupt), 'continue' (crash sau
    interrupt — chạy nốt), 'completed' (409).
    """
    from app.services.presidio_service import sanitize

    payload = dict(payload)
    if payload.get("reason"):
        payload["reason"] = sanitize(str(payload["reason"])).sanitized_text
    if payload.get("edited_insight") is not None:
        payload["edited_insight"] = {
            key: sanitize(str(value)).sanitized_text
            for key, value in payload["edited_insight"].items()
            if key in {"title", "finding"} and value is not None
        }
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
            values = dict(snap.values or {})
            interrupts = [
                intr.value
                for task in (getattr(snap, "tasks", None) or ())
                for intr in (getattr(task, "interrupts", ()) or ())
            ]
            logger.info(
                "get_run_snapshot run=%s values=%s next=%s interrupts=%s",
                run_id,
                list(values.keys()),
                list(snap.next or ()),
                [bool(i) for i in interrupts],
            )
            if not values:
                return None
            for intr in interrupts:
                if intr:
                    return intr
            return None

    try:
        return run_on_selector_loop(_flow)
    except Exception:  # noqa: BLE001 — GET status không được nổ
        logger.exception("get_run_snapshot fail")
        return None

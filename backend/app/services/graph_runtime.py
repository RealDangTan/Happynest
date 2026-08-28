"""LangGraph checkpointer runtime — tách từ hitl_graph cũ (strip 2026-08-28).

Plumbing AsyncPostgresSaver + Supabase DÙNG CHUNG cho mọi graph HITL:
- Phase 13/19 cũ đã bị strip; UNDERSTAND (plan 25) tái sử dụng nguyên pattern.
- Sống sót nguyênxi quirks S5 (decisions.md 2026-08-24):
  * async psycopg CHỈ chạy trên SelectorEventLoop — mọi thao tác graph chạy
    `asyncio.run(..., loop_factory=SelectorEventLoop)`, không đụng loop uvicorn.
  * Connection psycopg bám loop nơi nó được tạo → MỖI request mở saver riêng
    trên loop riêng, KHÔNG tái dùng saver toàn cục xuyên loop.
  * `ensure_checkpointer_ready()` tạo 4 bảng checkpoint ĐÚNG MỘT LẦN mỗi
    process — lifespan chỉ GỌI NÓ TRONG BACKGROUND THREAD (lifespan Windows
    chạy ProactorEventLoop mà async psycopg không chịu); request đầu nếu chưa
    setup cũng tự gọi lại (thread-safe qua lock).
"""

import asyncio
import logging
import selectors
import threading

logger = logging.getLogger(__name__)

_SETUP_DONE = {"ok": False}
_SETUP_LOCK = threading.Lock()


class CheckpointUnavailable(Exception):
    """Saver không kết nối được Supabase lúc setup — route chuyển 503."""


def _conn_string() -> str:
    """psycopg URI thuần cho AsyncPostgresSaver — bỏ prefix dialect SQLAlchemy."""
    from app.core.config import get_settings

    return get_settings().database_url_sqla.replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def run_on_selector_loop(coro_fn):
    """async psycopg bắt buộc SelectorEventLoop trên Windows (S5) — chạy coroutine
    trong loop RIÊNG, không đụng loop uvicorn. Gọi từ endpoint sync (threadpool)."""
    return asyncio.run(
        coro_fn(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )


async def _setup_coro() -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
        await saver.setup()


def ensure_checkpointer_ready() -> bool:
    """Tạo/idempotent 4 bảng checkpoint ĐÚNG MỘT lần mỗi process — thread-safe.

    ⚠️ KHÔNG được gọi trực tiếp trên event loop của uvicorn: lifespan Windows
    dùng ProactorEventLoop mà async psycopg chỉ chạy trên selector (S5) — vì
    vậy hàm tự chạy `asyncio.run` trên selector loop RIÊNG và lifespan chỉ
    gọi trong background thread (xem main.py). Trả True nếu sẵn sàng.
    """
    if _SETUP_DONE["ok"]:
        return True
    with _SETUP_LOCK:
        if _SETUP_DONE["ok"]:
            return True
        try:
            run_on_selector_loop(_setup_coro)
        except Exception as exc:  # noqa: BLE001 — caller quyết định fatal hay không
            logger.error("checkpoint saver setup failed: %s", type(exc).__name__)
            return False
        _SETUP_DONE["ok"] = True
        logger.info("checkpoint saver setup OK (bảng checkpoint sẵn sàng)")
        return True


def pending_interrupts(snap) -> list:
    """Interrupt đang đậu trong snapshot state (dùng cho GET status endpoint)."""
    tasks = getattr(snap, "tasks", None) or ()
    interrupts = []
    for task in tasks:
        interrupts.extend(getattr(task, "interrupts", ()) or ())
    return interrupts

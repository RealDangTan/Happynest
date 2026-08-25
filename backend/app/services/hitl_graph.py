"""HITL review graph — Phase 13 (13-hitl-langgraph.md §3.3).

Flow: prepare_review → interrupt(payload cho FE) → apply_action → record_correction? → END

Checkpoint: AsyncPostgresSaver nối thẳng Supabase (session pooler) — thread
sống sót restart process, resume bằng `Command(resume=…)` đúng như spike S5
đã chứng minh (decisions.md 2026-08-24).

⚠️ Windows quirk (S5): async psycopg CHỈ chạy trên SelectorEventLoop — mọi
thao tác graph chạy trong event loop RIÊNG qua `asyncio.run(…, loop_factory=
SelectorEventLoop)`, không đụng loop của uvicorn. Mỗi request mở saver riêng
trên loop riêng (connection psycopg bám loop nơi nó được tạo — tái dùng saver
toàn cục xuyên loop là lỗi kinh điển); `ensure_checkpointer_ready()` tạo sớm
4 bảng checkpoint ĐÚNG MỘT LẦN mỗi process — lifespan chỉ GỌI NÓ TRONG
BACKGROUND THREAD vì lifespan Windows chạy trên ProactorEventLoop mà async
psycopg không chịu (cùng gốc S5); request đầu tiên nếu chưa setup cũng tự gọi
lại (thread-safe qua lock) trước khi vào graph.

Idempotency node (crash giữa DB-commit và checkpoint-save ~9s WAN): hai INSERT
log trong record_correction mang marker `_thread` trong JSONB — node bị chạy
lại sau crash thấy marker trùng thì bỏ qua, không nhân bản side effect.

⚠️ PII boundary: interrupt payload chỉ chứa preview từ `sanitized_content`
(cắt 200 ký tự) + nhãn; log chỉ chứa id. Raw content không bao giờ vào
prompt/log/state.
"""

import asyncio
import logging
import selectors
import threading
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.db.session import SessionLocal
from app.models.correction_example import CorrectionExample
from app.models.enums import ReviewAction, ReviewStatus
from app.models.feedback import Feedback
from app.models.human_review import HumanReview

logger = logging.getLogger(__name__)

#: Độ dài preview content trong interrupt payload (đÃ sanitize).
_PREVIEW_CHARS = 200

_LABEL_KEYS = ("categories", "ai_issue", "severity", "sentiment")


class ReviewAlreadyCompleted(Exception):
    """Thread HITL đã hoàn tất mà vẫn nhận POST /reviews — route chuyển 409."""


class HitlState(TypedDict, total=False):
    feedback_id: str
    reviewer_id: str
    #: Nhãn + sanitized_content TRƯỚC khi review (chụp ở prepare_review).
    snapshot: dict[str, Any]
    #: {action, edited_content?, reason?} đến từ Command(resume=…).
    resume_payload: dict[str, Any]
    action: str
    final_status: str


# ---------------------------------------------------------------------------
# Seams thao tác DB — session ngắn mỗi lần (node cách nhau bởi checkpoint save
# ~9s qua WAN, KHÔNG giữ connection idle). Monkeypatch điểm này trong unit test.
# ---------------------------------------------------------------------------


def _load_feedback(feedback_id: uuid.UUID) -> Feedback | None:
    with SessionLocal() as db:
        return db.get(Feedback, feedback_id)


def _persist_sanitize(feedback_id: uuid.UUID, edited_text: str) -> dict[str, Any]:
    """edited_content đi qua Presidio TRƯỚC KHI lưu — raw người dùng gõ không
    bao giờ được ghi thẳng xuống `sanitized_content`."""
    from app.services.presidio_service import sanitize  # import muộn — init nặng

    result = sanitize(edited_text)
    updates = {
        "sanitized_content": result.sanitized_text,
        "pii_detected": result.pii_detected,
        "pii_entities": [e.model_dump() for e in result.entities],
    }
    with SessionLocal() as db:
        fb = db.get(Feedback, feedback_id)
        if fb is None:
            raise LookupError(f"feedback {feedback_id} biến mất giữa graph")
        for field, value in updates.items():
            setattr(fb, field, value)
        db.commit()
    return {"sanitized_content": updates["sanitized_content"], "pii_detected": updates["pii_detected"]}


def _set_status(feedback_id: uuid.UUID, status: ReviewStatus) -> None:
    with SessionLocal() as db:
        fb = db.get(Feedback, feedback_id)
        if fb is None:
            raise LookupError(f"feedback {feedback_id} biến mất giữa graph")
        fb.review_status = status
        db.commit()


def _review_exists(thread_id: str, action: str) -> bool:
    """Đã có dòng HumanReview do CÙNG thread graph ghi chưa (marker `_thread`)."""
    with SessionLocal() as db:
        hit = (
            db.query(HumanReview.id)
            .filter(
                HumanReview.feedback_id == uuid.UUID(thread_id.removeprefix("hitl-")),
                HumanReview.action == ReviewAction(action),
                HumanReview.original_value["_thread"].astext == thread_id,
            )
            .first()
        )
        return hit is not None


def _write_review_rows(
    *,
    thread_id: str,
    feedback_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    original: dict[str, Any],
    edited: dict[str, Any],
    action: str,
    reason: str | None,
    corrected_value: dict[str, Any],
) -> None:
    with SessionLocal() as db:
        db.add(
            HumanReview(
                feedback_id=feedback_id,
                original_value={**original, "_thread": thread_id},
                edited_value=edited,
                action=ReviewAction(action),
                reason=reason,
                reviewer_id=reviewer_id,
            )
        )
        db.add(
            CorrectionExample(
                feedback_id=feedback_id,
                original_prediction={**original, "_thread": thread_id},
                corrected_value=corrected_value,
                reason=reason,
            )
        )
        db.commit()


def _log_review_and_correction(**kwargs: Any) -> None:
    """Ghi 1 dòng HumanReview + 1 dòng CorrectionExample — idempotent theo
    `_thread`: node chạy lại sau crash không nhân bản (xem header module)."""
    if _review_exists(kwargs["thread_id"], kwargs["action"]):
        logger.info("hitl %s: log đã tồn tại — bỏ qua ghi lặp.", kwargs["thread_id"])
        return
    _write_review_rows(**kwargs)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def snapshot_of(fb: Feedback) -> dict[str, Any]:
    """Nhãn + content TRƯỚC review — nguồn cho original_value/corrected_value."""
    snap: dict[str, Any] = {
        "categories": list(fb.categories) if fb.categories is not None else None,
        "sanitized_content": fb.sanitized_content,
        "pii_detected": bool(fb.pii_detected),
    }
    for key in ("ai_issue", "sentiment", "severity"):
        value = getattr(fb, key)
        snap[key] = value.value if value is not None else None
    return snap


def build_graph(checkpointer):
    """Compile graph với checkpointer truyền vào (AsyncPostgresSaver prod /
    InMemorySaver unit test)."""

    def prepare_review(state: HitlState) -> dict[str, Any]:
        fb = _load_feedback(uuid.UUID(state["feedback_id"]))
        if fb is None:
            raise LookupError(f"feedback {state['feedback_id']} không tồn tại")
        snapshot = snapshot_of(fb)
        # Lần đầu: raise GraphInterrupt TẠI ĐÂY (snapshot chưa kịp trả về state).
        # Lần resume: node chạy LẠI từ đầu (đọc lại row — vẫn giá trị pre-review
        # vì apply_action chưa hề chạy), interrupt() trả payload và đi tiếp.
        resume_payload: dict[str, Any] = interrupt(
            {
                "feedback_id": state["feedback_id"],
                "labels": {k: snapshot[k] for k in _LABEL_KEYS},
                "content_preview": (snapshot["sanitized_content"] or "")[:_PREVIEW_CHARS],
                "pii_detected": snapshot["pii_detected"],
            }
        )
        return {"snapshot": snapshot, "resume_payload": dict(resume_payload)}

    def apply_action(state: HitlState) -> dict[str, Any]:
        payload = state["resume_payload"]
        action = payload["action"]
        fid = uuid.UUID(state["feedback_id"])
        if action == "approve":
            final = ReviewStatus.approved  # không đụng content
        elif action == "edit":
            _persist_sanitize(fid, payload["edited_content"])  # Presidio trước khi lưu
            final = ReviewStatus.edited
        elif action == "reject":
            final = ReviewStatus.rejected  # content nguyên vẹn
        else:  # phòng thủ — schema đã chặn, không bao giờ tới đây
            raise ValueError(f"action không hợp lệ: {action!r}")
        _set_status(fid, final)
        return {"action": action, "final_status": final.value}

    def record_correction(state: HitlState) -> dict[str, Any]:
        if state.get("action") not in ("edit", "reject"):
            return {}
        tid = f"hitl-{state['feedback_id']}"
        fid = uuid.UUID(state["feedback_id"])
        snapshot = state["snapshot"]
        post = snapshot_of(_load_feedback(fid))  # trạng thái SAU apply_action
        if state["action"] == "edit":
            # Ngữ nghĩa chốt plan §3.2: edit → NHÃN GIỮ NGUYÊN từ snapshot,
            # kèm sanitized_content MỚI (ví dụ dương text-mới/nhãn-cũ cho few-shot).
            corrected: dict[str, Any] = {k: snapshot[k] for k in _LABEL_KEYS}
            corrected["sanitized_content"] = post["sanitized_content"]
        else:
            # reject → tín hiệu ÂM hoàn toàn: "text này không có nhãn nào".
            corrected = {k: (None if k != "categories" else []) for k in _LABEL_KEYS}
        _log_review_and_correction(
            thread_id=tid,
            feedback_id=fid,
            reviewer_id=uuid.UUID(state["reviewer_id"]),
            original=snapshot,
            edited=post,
            action=state["action"],
            reason=state["resume_payload"].get("reason"),
            corrected_value=corrected,
        )
        return {}

    builder = StateGraph(HitlState)
    builder.add_node("prepare_review", prepare_review)
    builder.add_node("apply_action", apply_action)
    builder.add_node("record_correction", record_correction)
    builder.add_edge(START, "prepare_review")
    builder.add_edge("prepare_review", "apply_action")
    builder.add_conditional_edges(
        "apply_action",
        lambda s: "record_correction" if s.get("action") in ("edit", "reject") else END,
    )
    builder.add_edge("record_correction", END)
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Event-loop plumbing (S5 quirks) + orchestration per-request
# ---------------------------------------------------------------------------

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


def _run_on_selector_loop(coro_fn):
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
            _run_on_selector_loop(_setup_coro)
        except Exception as exc:  # noqa: BLE001 — caller quyết định fatal hay không
            logger.error("checkpoint saver setup failed: %s", type(exc).__name__)
            return False
        _SETUP_DONE["ok"] = True
        logger.info("checkpoint saver setup OK (bảng checkpoint sẵn sàng)")
        return True


def _pending_interrupts(snap) -> list:
    tasks = getattr(snap, "tasks", None) or ()
    interrupts = []
    for task in tasks:
        interrupts.extend(getattr(task, "interrupts", ()) or ())
    return interrupts


def _next_graph_step(snap) -> str:
    """Phân loại trạng thái thread: start | resume | continue | completed.

    - start: thread chưa tồn tại (values rỗng — chưa superstep nào được ghi).
    - resume: đang đậu tại interrupt của prepare_review (case thường + case
      crash-ngay-tại-interrupt).
    - continue: crash SAU khi interrupt đã tiêu thụ nhưng graph chưa hết —
      resume_payload đã nằm trong checkpoint, chạy nốt không cần payload mới.
    - completed: đã review xong → caller phải 409.
    """
    values = getattr(snap, "values", None) or {}
    nxt = list(getattr(snap, "next", None) or ())
    if not values:
        return "start"
    if _pending_interrupts(snap) or nxt == ["prepare_review"]:
        return "resume"
    if nxt:
        return "continue"
    return "completed"


def submit_review(feedback_id: uuid.UUID, reviewer_id: uuid.UUID, payload: dict) -> dict:
    """Chạy flow POST /api/reviews/{feedback_id}: đảm bảo thread đang đậu ở
    interrupt rồi resume bằng payload; trả state cuối (final_status...).
    Raise ReviewAlreadyCompleted nếu thread đã hoàn tất,
    CheckpointUnavailable nếu bảng checkpoint chưa dựng được (→ 503)."""
    # Sync context (threadpool của route) — gọi TRƯỚC khi vào selector loop để
    # request đầu không phải trả giá setup trong coroutine (~9s WAN × 2).
    if not ensure_checkpointer_ready():
        raise CheckpointUnavailable(
            "Không kết nối được Supabase để dựng bảng checkpoint LangGraph."
        )

    async def _flow() -> dict:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        config = {"configurable": {"thread_id": f"hitl-{feedback_id}"}}
        async with AsyncPostgresSaver.from_conn_string(_conn_string()) as saver:
            if not _SETUP_DONE["ok"]:
                await saver.setup()
            graph = build_graph(saver)

            step = _next_graph_step(await graph.aget_state(config))
            if step == "start":
                logger.info("hitl %s: thread mới — invoke tới interrupt.", config)
                await graph.ainvoke(
                    {
                        "feedback_id": str(feedback_id),
                        "reviewer_id": str(reviewer_id),
                    },
                    config,
                )
                step = _next_graph_step(await graph.aget_state(config))
            if step == "resume":
                logger.info("hitl %s: resume với action=%s.", config, payload.get("action"))
                await graph.ainvoke(Command(resume=dict(payload)), config)
            elif step == "continue":
                logger.info("hitl %s: crash giữa chừng — chạy nốt graph.", config)
                await graph.ainvoke(None, config)
            else:
                raise ReviewAlreadyCompleted(
                    f"Thread HITL {config['configurable']['thread_id']} đã hoàn tất."
                )

            return dict((await graph.aget_state(config)).values or {})

    return _run_on_selector_loop(_flow)

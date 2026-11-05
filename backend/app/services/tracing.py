"""Tracing hai lớp — Langfuse Cloud EU + writer bảng `llm_call_logs`.

Lịch sử file: Phase 08 dựng scaffold chỉ có `write_llm_call_log` (vì embedder
chạy trước 05/07 cần log call); Phase 07 MỞ RỘNG đúng theo ghi chú scaffold —
giữ nguyên hợp đồng writer (caller tự commit session, trả về row) — bổ sung:
client Langfuse v3 singleton + wrapper `trace_llm_call(...)` + kill-switch
`LANGFUSE_TRACING_ENABLED=false` + `flush()` neo vào lifespan shutdown.

Quyết định đã khóa (execute-plan §1): bảng Postgres là bằng chứng vĩnh viễn
vendor-independent; Langfuse chỉ là dashboard quan sát. llm_client ghi CẢ HAI.

⚠️ PII boundary:
- Bảng `llm_call_logs` chỉ chứa METADATA call — không bao giờ prompt/response.
- `trace_llm_call(input_text_sanitized=...)`: caller PHẢI truyền text đã sanitize
  — không kiểm tra được kỹ thuật nên tên tham số + docstring là hợp đồng quy trình.

Kill-switch: `LANGFUSE_TRACING_ENABLED=false` hoặc thiếu key → mọi hàm trace
thành no-op, app vẫn chạy bình thường (tiêu chí nghiệm thu phase 07).
"""

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import LlmCallType
from app.models.llm_call_log import LlmCallLog

logger = get_logger(__name__)

_langfuse: Any | None = None  # client singleton (Any để import-time không đụng SDK)
_langfuse_lock = Lock()
_call_capture: ContextVar[tuple[list[dict], Any, Any] | None] = ContextVar("call_capture", default=None)


@contextmanager
def capture_call_logs(*, analysis_run_id=None, feedback_id=None):
    """Worker-local metadata only; caller persists it with the item's result.

    ContextVars isolate concurrent workers and nested scopes. No prompt/response
    is buffered, and callers outside this context retain immediate log commits.
    """
    rows: list[dict] = []
    token = _call_capture.set((rows, analysis_run_id, feedback_id))
    try:
        yield rows
    finally:
        _call_capture.reset(token)


def record_call_log(session_factory, **metadata) -> None:
    capture = _call_capture.get()
    if capture is not None:
        rows, run_id, feedback_id = capture
        metadata["analysis_run_id"] = metadata.get("analysis_run_id") or run_id
        metadata["feedback_id"] = metadata.get("feedback_id") or feedback_id
        rows.append(metadata)
        return
    with session_factory() as session:
        write_llm_call_log(session, **metadata)
        session.commit()


# ---------------------------------------------------------------------------
# Lớp 1 — Langfuse (dashboard quan sát, EU)
# ---------------------------------------------------------------------------

def get_langfuse() -> Any | None:
    """Client Langfuse v3 lazy-init; None = tracing tắt (kill-switch/thiếu key)."""
    global _langfuse
    settings = get_settings()
    if not settings.LANGFUSE_TRACING_ENABLED:
        return None
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None
    with _langfuse_lock:
        if _langfuse is None:
            from langfuse import Langfuse  # import muộn — không tốn gì khi kill-switch

            _langfuse = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_BASE_URL,
            )
    return _langfuse


#: Trần ký tự cho payload I/O gửi Langfuse (chỉ text ĐÃ SANITIZE). 2000 cũ cắt
#: mất evidence/tool_history của prompt planner (~8–10k ký tự) → trace không đọc
#: được vì sao agent chọn bước đó (audit 2026-11-04).
_IO_MAX_CHARS = 20000
_SYSTEM_MAX_CHARS = 6000

#: call_type → tên trace/pipeline hiển thị trên Langfuse (thay vì tên từng call).
_PIPELINE_BY_CALL_TYPE = {
    "classify": "listen-analysis",
    "enrich": "listen-analysis",
    "embed": "listen-analysis",
    "plan": "understand",
    "evaluate": "understand",
    "synthesize": "understand",
    "route": "understand",
    "critic": "understand",
    "act_generate": "act",
    "schema_map": "import-mapping",
    "name_cluster": "clustering",
    "generate_insight": "understand",
    "taxonomy_generate": "taxonomy",
    "topic_recommend": "taxonomy",
}

#: Scope trace tường minh cho call KHÔNG mang analysis_run_id (ACT, mapping…):
#: {"seed": str, "name": str | None, "metadata": dict}. ContextVar → cô lập thread.
_trace_scope: ContextVar[dict | None] = ContextVar("langfuse_trace_scope", default=None)


@contextmanager
def trace_scope(*, seed: Any, name: str | None = None, metadata: dict | None = None):
    """Gom mọi call LLM trong khối vào MỘT trace Langfuse có id tất định theo `seed`.

    Dùng cho call không truyền analysis_run_id (vd. ACT sinh action cho insight của
    run X → seed=run X để action nằm chung trace điều tra). Không chạm llm_call_logs.
    """
    token = _trace_scope.set({"seed": str(seed), "name": name, "metadata": metadata or {}})
    try:
        yield
    finally:
        _trace_scope.reset(token)


def _resolve_trace(lf: Any, analysis_run_id: Any | None) -> tuple[dict | None, str | None, dict]:
    """(trace_context, trace_name_override, extra_metadata) cho observation hiện hành.

    Ưu tiên scope tường minh; không có scope → seed = analysis_run_id, nên MỌI call
    + tool span + event của một run (kể cả resume Gate #2 ở thread khác, sau restart)
    rơi vào cùng một trace. Không có cả hai → None (trace riêng như cũ)."""
    scope = _trace_scope.get()
    if scope is not None:
        return {"trace_id": lf.create_trace_id(seed=scope["seed"])}, scope["name"], scope["metadata"]
    if analysis_run_id:
        return {"trace_id": lf.create_trace_id(seed=str(analysis_run_id))}, None, {}
    return None, None, {}


def run_trace_id(run_id: Any) -> str | None:
    """Trace id Langfuse tất định của một analysis run (None khi tracing tắt)."""
    lf = get_langfuse()
    if lf is None or not run_id:
        return None
    return lf.create_trace_id(seed=str(run_id))


def _io(system_prompt: str | None, user_text: str) -> Any:
    if system_prompt is None:
        return (user_text or "")[:_IO_MAX_CHARS]
    return {
        "system": system_prompt[:_SYSTEM_MAX_CHARS],
        "user": (user_text or "")[:_IO_MAX_CHARS],
    }


def _usage_details(usage: dict[str, int] | None) -> dict[str, int] | None:
    """{"prompt","completion"} nội bộ → khóa usage_details của Langfuse v3.

    Bản cũ truyền `usage=` (không có trong chữ ký v3, rơi vào **kwargs) nên token
    + cost KHÔNG BAO GIỜ lên dashboard (audit 2026-11-04)."""
    if not usage:
        return None
    prompt, completion = int(usage.get("prompt") or 0), int(usage.get("completion") or 0)
    return {"input": prompt, "output": completion, "total": prompt + completion}


def start_llm_observation(
    *,
    name: str,
    model: str,
    input_text_sanitized: str,
    system_prompt: str | None = None,
    call_type: Any | None = None,
    prompt_version: str | None = None,
    analysis_run_id: Any | None = None,
    feedback_id: Any | None = None,
    attempt: str | None = None,
) -> Any | None:
    """Mở generation TRƯỚC khi gọi provider để start/end time phản ánh latency thật
    (SDK v3 không cho đặt start_time lùi). Trả handle cho `trace_llm_call(observation=…)`;
    None khi tracing tắt hoặc lỗi. Không bao giờ raise.

    ⚠️ `input_text_sanitized`/`system_prompt` PHẢI là text đã sanitize/tĩnh."""
    lf = get_langfuse()
    if lf is None:
        return None
    call_type_value = getattr(call_type, "value", call_type)
    try:
        ctx, scope_name, scope_meta = _resolve_trace(lf, analysis_run_id)
        metadata = {
            "call_type": call_type_value,
            "prompt_version": prompt_version,
            "analysis_run_id": str(analysis_run_id) if analysis_run_id else None,
            "feedback_id": str(feedback_id) if feedback_id else None,
            "attempt": attempt,
            **scope_meta,
        }
        gen = lf.start_generation(
            trace_context=ctx,
            name=name,
            model=model,
            input=_io(system_prompt, input_text_sanitized),
            metadata={k: v for k, v in metadata.items() if v is not None},
            version=prompt_version,
        )
        trace_name = scope_name or _PIPELINE_BY_CALL_TYPE.get(call_type_value or "", None)
        if ctx is None or scope_name or analysis_run_id:
            gen.update_trace(
                name=trace_name,
                metadata={k: v for k, v in metadata.items() if k in ("analysis_run_id",) and v},
                tags=[trace_name] if trace_name else None,
            )
        return gen
    except Exception as exc:  # noqa: BLE001 — mọi lỗi trace chỉ warn
        logger.warning("langfuse start generation failed: %s", type(exc).__name__)
        return None


def trace_llm_call(
    *,
    name: str,
    input_text_sanitized: str,
    output_summary: str,
    usage: dict[str, int] | None,
    latency_ms: int,
    model: str,
    prompt_version: str,
    error: str | None = None,
    observation: Any | None = None,
    call_type: Any | None = None,
    analysis_run_id: Any | None = None,
    feedback_id: Any | None = None,
) -> None:
    """Đóng (hoặc tạo-rồi-đóng) một generation trên Langfuse. Không bao giờ raise —
    tracing không được phá pipeline. `usage` dạng {"prompt": n, "completion": n}.

    `observation` = handle từ `start_llm_observation` (timeline đúng). Thiếu handle
    → tạo generation ngay lúc này (tương thích caller cũ)."""
    try:
        gen = observation or start_llm_observation(
            name=name,
            model=model,
            input_text_sanitized=input_text_sanitized,
            call_type=call_type,
            prompt_version=prompt_version,
            analysis_run_id=analysis_run_id,
            feedback_id=feedback_id,
        )
        if gen is None:
            return
        gen.update(
            output=(output_summary or "")[:_IO_MAX_CHARS],
            model=model,
            usage_details=_usage_details(usage),
            metadata={"latency_ms": latency_ms},
            level="ERROR" if error else "DEFAULT",
            status_message=(error or "")[:500] or None,
        )
        gen.end()
    except Exception as exc:  # noqa: BLE001 — mọi lỗi trace chỉ warn
        logger.warning("langfuse trace failed: %s", type(exc).__name__)


@contextmanager
def trace_span(
    *,
    run_id: Any,
    name: str,
    input: Any = None,
    metadata: dict | None = None,
    trace_name: str | None = None,
):
    """Span non-LLM (tool của agent, node quyết định) trong trace của run.

    `trace_name`: gắn tên trace tường minh — Langfuse lấy tên trace từ observation
    gốc mới nhất KHÔNG mang trace name (e2e 2026-11-05: trace điều tra bị đổi tên
    thành "act_generate:…"), nên mọi observation của trace phải mang tên.
    Yield handle có `.update(...)` hoặc None (tracing tắt); lỗi trace chỉ warn.
    Exception của khối được ghi level ERROR rồi raise lại nguyên vẹn."""
    lf = get_langfuse()
    span = None
    if lf is not None:
        try:
            ctx, scope_name, scope_meta = _resolve_trace(lf, run_id)
            span = lf.start_span(
                trace_context=ctx, name=name, input=input,
                metadata={**(metadata or {}), **scope_meta} or None,
            )
            if trace_name or scope_name:
                span.update_trace(name=trace_name or scope_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse span failed: %s", type(exc).__name__)
            span = None
    try:
        yield span
    except BaseException as exc:
        if span is not None:
            try:
                span.update(level="ERROR", status_message=f"{type(exc).__name__}"[:500])
            except Exception:  # noqa: BLE001
                pass
        raise
    finally:
        if span is not None:
            try:
                span.end()
            except Exception as exc:  # noqa: BLE001
                logger.warning("langfuse span end failed: %s", type(exc).__name__)


def trace_event(
    *,
    run_id: Any,
    name: str,
    output: Any = None,
    metadata: dict | None = None,
    level: str = "DEFAULT",
    trace_update: dict | None = None,
    trace_name: str | None = None,
) -> None:
    """Event tức thời (quyết định deterministic của planner, Gate #2…) trong trace
    của run; `trace_update` (name/input/output/metadata/tags) gắn lên trace."""
    try:
        with trace_span(run_id=run_id, name=name, metadata=metadata,
                        trace_name=trace_name) as span:
            if span is None:
                return
            span.update(output=output, level=level)
            if trace_update:
                span.update_trace(**trace_update)
    except Exception as exc:  # noqa: BLE001
        logger.warning("langfuse event failed: %s", type(exc).__name__)


def trace_score(*, run_id: Any, name: str, value: Any, comment: str | None = None) -> None:
    """Score CATEGORICAL/NUMERIC lên trace của run (vd. quyết định Gate #2)."""
    lf = get_langfuse()
    if lf is None or not run_id:
        return
    try:
        lf.create_score(
            trace_id=lf.create_trace_id(seed=str(run_id)),
            name=name,
            value=value,
            data_type="CATEGORICAL" if isinstance(value, str) else "NUMERIC",
            comment=(comment or None) and comment[:500],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("langfuse score failed: %s", type(exc).__name__)


def flush() -> None:
    """Đẩy batch trace còn treo — gọi ở lifespan shutdown thay langfuse.shutdown()."""
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse flush failed: %s", type(exc).__name__)


# ---------------------------------------------------------------------------
# Lớp 2 — llm_call_logs trong Postgres (bằng chứng vĩnh viễn)
# ---------------------------------------------------------------------------

def write_llm_call_log(
    session: Session,
    *,
    analysis_run_id: uuid.UUID | None = None,
    feedback_id: uuid.UUID | None = None,
    call_type: LlmCallType | str,
    prompt_version: str,
    model: str,
    latency_ms: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> LlmCallLog:
    """INSERT 1 row llm_call_logs; caller tự commit session của mình.

    ⚠️ KHÔNG BAO GIỜ lưu prompt/response content (chỉ metadata). Raise cho caller
    quyết định — llm_client bọc try/except vì log-fail không được phép chết call chính.
    """
    row = LlmCallLog(
        analysis_run_id=analysis_run_id,
        feedback_id=feedback_id,
        call_type=call_type,
        prompt_version=prompt_version,
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        error=error,
    )
    session.add(row)
    return row

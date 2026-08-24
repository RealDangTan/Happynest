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
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import LlmCallType
from app.models.llm_call_log import LlmCallLog

logger = get_logger(__name__)

_langfuse: Any | None = None  # client singleton (Any để import-time không đụng SDK)


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
    if _langfuse is None:
        from langfuse import Langfuse  # import muộn — không tốn gì khi kill-switch

        _langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_BASE_URL,
        )
    return _langfuse


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
) -> None:
    """Ghi một generation lên Langfuse. Không bao giờ raise — tracing không được
    phá pipeline. `usage` dạng {"prompt": n, "completion": n} hoặc None khi lỗi."""
    lf = get_langfuse()
    if lf is None:
        return
    try:
        gen = lf.start_generation(
            name=name,
            input=input_text_sanitized[:2000],  # hygiene payload — chỉ sanitized
            metadata={
                "model": model,
                "prompt_version": prompt_version,
                "latency_ms": latency_ms,
            },
        )
        gen.update(
            output=(output_summary or "")[:1000],
            usage=usage,
            level="ERROR" if error else "DEFAULT",
            status_message=(error or "")[:500] or None,
        )
        gen.end()
    except Exception as exc:  # noqa: BLE001 — mọi lỗi trace chỉ warn
        logger.warning("langfuse trace failed: %s", type(exc).__name__)


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

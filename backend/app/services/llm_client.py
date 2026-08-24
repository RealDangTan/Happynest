"""LLM chat client — chuỗi fallback cấu trúc đầu ra ĐÃ KHÓA (execute-plan §1):

    Mode A: response_format=json_schema (strict)  ← mặc định, S2 chứng minh 10/10
      ↓ provider lỗi / JSON hỏng
    Mode B: prompt-JSON + strip code fence + Pydantic validate
      ↓ ValidationError
    retry MỘT lần kèm text lỗi validate
      ↓ vẫn fail
    LLMStructureError

Sau MỖI call API (kể cả call lỗi): đo latency, lấy usage, ghi `llm_call_logs`
+ Langfuse generation; cập nhật module state `_structured_output_mode` cho
`/api/health`.

⚠️⚠️ HỢP ĐỒNG PII (Hard Rule): `system`/`user` PHẢI là text ĐÃ SANITIZE —
client không nhận raw content bao giờ. Không kiểm tra được kỹ thuật nên đây là
hợp đồng quy trình; caller (sanitize → classify) chịu trách nhiệm.
"""

import json
import re
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import LlmCallType
from app.services import tracing

logger = get_logger(__name__)

# --- Module state cho /api/health ("json_schema" | "prompt_json" | None) ---
_structured_output_mode: str | None = None

_client: Any | None = None

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")
_BRACE_RE = re.compile(r"\{.*\}", re.S)


class LLMStructureError(RuntimeError):
    """Cả fallback chain thất bại — model không trả JSON hợp lệ sau retry."""


def _get_client() -> Any:
    """OpenAI SDK client singleton, base_url override theo locked decision."""
    global _client
    if _client is None:
        from openai import OpenAI  # import muộn — unit test không cần network stack

        settings = get_settings()
        if not settings.LLM_BASE_URL or not settings.LLM_API_KEY:
            raise RuntimeError(
                "LLM chưa cấu hình: cần LLM_BASE_URL + LLM_API_KEY trong .env"
            )
        _client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=120,
            max_retries=1,  # SDK-level retry tắt gần hết — retry do chain tự quản
        )
    return _client


def _extract_json(text: str) -> str:
    """Strip code fence rồi bóc object JSON ngoài cùng (Mode B)."""
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    m = _BRACE_RE.search(cleaned)
    return m.group(0) if m else cleaned


def _api_call(
    messages: list[dict[str, str]], response_format: dict | None
) -> tuple[str, dict[str, int] | None]:
    """Một call API thô. Trả (content, usage-dict); raise khi provider lỗi."""
    kwargs: dict[str, Any] = {
        "model": get_settings().LLM_MODEL,
        "messages": messages,
        "temperature": 0,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    resp = _get_client().chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    usage = None
    raw_usage = getattr(resp, "usage", None)
    if raw_usage is not None:
        usage = {
            "prompt": getattr(raw_usage, "prompt_tokens", 0) or 0,
            "completion": getattr(raw_usage, "completion_tokens", 0) or 0,
        }
    return content, usage


def _record_attempt(  # noqa: PLR0913 — metadata call đủ đầy quan trọng hơn gọn chữ ký
    *,
    name: str,
    input_text_sanitized: str,
    output_text: str,
    schema_name: str,
    call_type: LlmCallType,
    prompt_version: str,
    model: str,
    latency_ms: int,
    usage: dict[str, int] | None,
    error: str | None,
    feedback_id: Any | None,
    analysis_run_id: Any | None,
    session_factory: Any,
) -> None:
    """Ghi CẢ HAI lớp trace cho một attempt. Log-fail chỉ warn — không phá pipeline."""
    error_short = error[:500] if error else None
    try:
        tracing.trace_llm_call(
            name=name,
            input_text_sanitized=input_text_sanitized,
            output_summary=(output_text or error or "")[:1000],
            usage=usage,
            latency_ms=latency_ms,
            model=model,
            prompt_version=prompt_version,
            error=error_short,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("trace layer failed: %s", type(exc).__name__)
    try:
        with session_factory() as session:
            tracing.write_llm_call_log(
                session,
                analysis_run_id=analysis_run_id,
                feedback_id=feedback_id,
                call_type=call_type,
                prompt_version=prompt_version,
                model=model,
                latency_ms=latency_ms,
                prompt_tokens=usage["prompt"] if usage else None,
                completion_tokens=usage["completion"] if usage else None,
                error=error_short,
            )
            session.commit()  # hợp đồng writer: caller tự commit
    except Exception as exc:  # noqa: BLE001 — DB log fail không được chết call chính
        logger.error("llm_call_logs write failed: %s: %s", type(exc).__name__, exc)


def chat_structured(
    system: str,
    user: str,
    schema: type[BaseModel],
    *,
    call_type: LlmCallType = LlmCallType.classify,
    prompt_version: str,
    feedback_id: Any | None = None,
    analysis_run_id: Any | None = None,
    session_factory: Any | None = None,
) -> BaseModel:
    """Gọi LLM chat ép đầu ra khớp `schema` theo fallback chain khóa ở header.

    ⚠️ `system`/`user` phải là text ĐÃ SANITIZE (xem hợp đồng PII đầu module).

    `call_type`/`prompt_version`: metadata ghi llm_call_logs (classifier truyền
    LlmCallType.classify + PROMPT_VERSION của nó). `session_factory` inject được
    cho unit test — mặc định SessionLocal ứng dụng.
    """
    global _structured_output_mode
    from app.db.session import SessionLocal

    factory = session_factory or SessionLocal
    settings = get_settings()
    model_name = settings.LLM_MODEL
    name = f"{call_type.value}:{schema.__name__}"
    base_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    common = dict(
        input_text_sanitized=user,
        call_type=call_type,
        prompt_version=prompt_version,
        model=model_name,
        feedback_id=feedback_id,
        analysis_run_id=analysis_run_id,
        session_factory=factory,
    )

    def validate(content: str) -> BaseModel:
        return schema.model_validate_json(_extract_json(content))

    # ---- Mode A: json_schema strict (S2: provider honor 10/10) ----
    fmt = {
        "type": "json_schema",
        "json_schema": {
            "name": schema.__name__,
            "strict": True,
            "schema": _schema_for(schema),
        },
    }
    t0 = time.perf_counter()
    a_error: str | None = None
    result: BaseModel | None = None
    usage_a: dict[str, int] | None = None
    try:
        content_a, usage_a = _api_call(base_messages, fmt)
    except Exception as exc:  # noqa: BLE001 — mọi provider error đều rơi xuống Mode B
        a_error = f"provider: {type(exc).__name__}: {exc}"
        latency = int((time.perf_counter() - t0) * 1000)
        logger.warning("Mode A rejected (%s) → Mode B", a_error[:120])
        _structured_output_mode = "prompt_json"
        _record_attempt(
            name=name, output_text="", latency_ms=latency, usage=None,
            error=a_error, schema_name=schema.__name__, **common,
        )
    else:
        latency = int((time.perf_counter() - t0) * 1000)
        try:
            result = validate(content_a)
            _structured_output_mode = "json_schema"
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            a_error = f"validate: {str(exc)[:300]}"
        _record_attempt(
            name=name,
            output_text=content_a,
            latency_ms=latency,
            usage=usage_a,
            error=a_error,
            schema_name=schema.__name__,
            **common,
        )
        if result is not None:
            return result

    # ---- Mode B: prompt-JSON + Pydantic validate (+ 1 retry kèm lỗi) ----
    b_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {
            "role": "user",
            "content": (
                "Trả về CHỈ một JSON object hợp lệ khớp schema sau "
                f"(không markdown fence, không text thừa): "
                f"{json.dumps(_schema_for(schema), ensure_ascii=False)}"
            ),
        },
    ]
    last_error = a_error
    for attempt in range(2):
        t0 = time.perf_counter()
        b_error: str | None = None
        content_b, usage_b = "", None
        try:
            content_b, usage_b = _api_call(b_messages, None)
        except Exception as exc:  # noqa: BLE001
            b_error = f"provider: {type(exc).__name__}: {exc}"
            latency = int((time.perf_counter() - t0) * 1000)
            _record_attempt(
                name=name, output_text="", latency_ms=latency, usage=None,
                error=b_error, schema_name=schema.__name__, **common,
            )
            last_error = b_error
            break  # provider chết thì retry cũng chết — dừng sớm
        latency = int((time.perf_counter() - t0) * 1000)
        try:
            result = validate(content_b)
            _structured_output_mode = "prompt_json"
            _record_attempt(
                name=name, output_text=content_b, latency_ms=latency,
                usage=usage_b, error=None,
                schema_name=schema.__name__, **common,
            )
            return result
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            b_error = f"validate: {str(exc)[:300]}"
            last_error = b_error
            _record_attempt(
                name=name, output_text=content_b, latency_ms=latency,
                usage=usage_b, error=b_error,
                schema_name=schema.__name__, **common,
            )
            if attempt == 0:  # retry đúng MỘT lần kèm text lỗi
                b_messages.append({"role": "assistant", "content": content_b[:500]})
                b_messages.append({
                    "role": "user",
                    "content": f"JSON trước sai lỗi: {b_error}. "
                               "Trả về lại JSON object đã sửa, CHỈ JSON thôi.",
                })

    raise LLMStructureError(
        f"Fallback chain thất bại sau Mode A + Mode B + 1 retry. Lỗi cuối: {last_error}"
    )


_SCHEMA_CACHE: dict[type[BaseModel], dict] = {}


def _schema_for(schema: type[BaseModel]) -> dict:
    """JSON schema phẳng cho Mode A. Taxonomy có bản tay tối ưu strict-mode;
    schema khác dùng model_json_schema chung (đủ chuẩn OpenAI strict)."""
    if schema not in _SCHEMA_CACHE:
        from app.schemas.taxonomy import Classification, strict_classification_schema

        _SCHEMA_CACHE[schema] = (
            strict_classification_schema()
            if schema is Classification
            else schema.model_json_schema()
        )
    return _SCHEMA_CACHE[schema]

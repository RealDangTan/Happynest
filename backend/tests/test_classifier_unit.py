"""Unit tests Phase 07 — classifier + fallback chain + llm_call_logs.

Nguyên tắc: KHÔNG network (fake OpenAI client), KHÔNG đụng Supabase dev
(row-log test dùng sqlite in-memory qua `session_factory` inject của
chat_structured). Tracing thật bị vô hiệu hóa bằng autouse fixture — kill-switch
được test riêng ở cuối file với settings monkeypatch.

Reshape 2026-08-28: test công thức HITL đã bỏ cùng feedback-level HITL.
"""

import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.models.enums import LlmCallType, Severity
from app.schemas.taxonomy import Classification
from app.services import llm_client, tracing
from app.services.classifier import (
    PROMPT_VERSION,
    classify_feedback,
)
from app.services.llm_client import LLMStructureError

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

VALID_JSON = json.dumps(
    {
        "categories": ["dịch thuật"],
        "ai_issue": "inaccuracy",
        "sentiment": "negative",
        "severity": "high",
        "safety_issue": False,
        "confidence": 0.9,
        "rationale": "Bản dịch sai hoàn toàn đoạn văn quan trọng.",
    },
    ensure_ascii=False,
)

INVALID_JSON = json.dumps({"sentiment": "negative", "severity": "catastrophic"})


def _resp(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34),
    )


class FakeOpenAI:
    """Client giả theo kịch bản (script): item = content str | Exception."""

    def __init__(self, script: list):
        self.script = list(script)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0) if self.script else RuntimeError("hết kịch bản")
        if isinstance(step, Exception):
            raise step
        return _resp(step)


@pytest.fixture()
def no_real_tracing(monkeypatch):
    """Chặn Langfuse thật trong mọi test chain (keys thật có trong .env)."""
    monkeypatch.setattr(tracing, "get_langfuse", lambda: None)


@pytest.fixture(autouse=True)
def no_real_db(monkeypatch):
    """Chặn ghi llm_call_logs vào Supabase dev từ mọi nhánh log mặc định.

    chat_structured import SessionLocal TẠI THỜI ĐIỂM gọi nên patch attr
    module `app.db.session` có hiệu lực. Conftest (auth) giữ tham chiếu gốc
    từ trước — không bị ảnh hưởng.
    """
    from app.db import session as db_session
    from app.models.llm_call_log import LlmCallLog

    sink_engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    LlmCallLog.__table__.create(sink_engine)
    monkeypatch.setattr(db_session, "SessionLocal", sessionmaker(bind=sink_engine))


@pytest.fixture(autouse=True)
def clean_module_state():
    llm_client._structured_output_mode = None
    yield
    llm_client._structured_output_mode = None


def _wire(monkeypatch, fake: FakeOpenAI) -> FakeOpenAI:
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

def test_mode_a_json_schema_success(monkeypatch, no_real_tracing):
    fake = _wire(monkeypatch, FakeOpenAI([VALID_JSON]))

    result = classify_feedback("App dịch sai đoạn văn.")

    assert isinstance(result, Classification)
    assert result.severity is Severity.high
    assert result.ai_issue.value == "inaccuracy"
    assert result.confidence == pytest.approx(0.9)
    assert result.safety_issue is False
    # đúng 1 call, Mode A có response_format json_schema strict + temperature=0
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["temperature"] == 0
    rf = call["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert llm_client._structured_output_mode == "json_schema"


def test_provider_rejects_response_format_falls_back_to_prompt_json(
    monkeypatch, no_real_tracing
):
    fake = _wire(
        monkeypatch,
        FakeOpenAI([
            RuntimeError("400 response_format is not supported"),
            VALID_JSON,
        ]),
    )

    result = classify_feedback("App dịch sai.")

    assert isinstance(result, Classification)
    assert len(fake.calls) == 2
    # Call thứ 2 (Mode B): không response_format, user msg chứa schema + chỉ thị
    b_call = fake.calls[1]
    assert "response_format" not in b_call
    joined = " ".join(m["content"] for m in b_call["messages"])
    assert "CHỈ một JSON object hợp lệ" in joined
    assert '"severity"' in joined  # schema được nhúng vào prompt
    assert llm_client._structured_output_mode == "prompt_json"


def test_validation_error_retry_once_with_error_text_then_success(
    monkeypatch, no_real_tracing
):
    bad = json.dumps({"categories": [], "severity": "high"})  # thiếu field + rỗng
    fake = _wire(monkeypatch, FakeOpenAI([bad, bad, VALID_JSON]))

    result = classify_feedback("App chậm.")

    assert isinstance(result, Classification)
    assert len(fake.calls) == 3  # A + B lần 1 + B retry
    # Message retry phải mang text lỗi validate về JSON trước
    last_user = [
        m["content"] for m in fake.calls[2]["messages"] if m["role"] == "user"
    ][-1]
    assert "JSON trước sai lỗi" in last_user
    assert llm_client._structured_output_mode == "prompt_json"


def test_chain_exhausted_raises_llm_structure_error(monkeypatch, no_real_tracing):
    err = RuntimeError("500 upstream dead")
    _wire(monkeypatch, FakeOpenAI([err, err]))  # A fail + B fail (provider chết)

    with pytest.raises(LLMStructureError):
        classify_feedback("App chậm.")


def test_three_invalid_outputs_exhaust_retries_and_raise(monkeypatch, no_real_tracing):
    bad = json.dumps({"severity": "không-hợp-lệ"})
    _wire(monkeypatch, FakeOpenAI([bad, bad, bad]))  # A + B + B-retry đều hỏng

    with pytest.raises(LLMStructureError):
        classify_feedback("App chậm.")


# ---------------------------------------------------------------------------
# llm_call_logs row (sqlite in-memory — không đụng Supabase)
# ---------------------------------------------------------------------------

def test_llm_call_log_row_written_with_metadata(monkeypatch, no_real_tracing):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    from app.db.base import Base
    from app.models.llm_call_log import LlmCallLog

    LlmCallLog.__table__.create(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    fake = _wire(monkeypatch, FakeOpenAI([VALID_JSON]))
    fb_id = uuid.uuid4()

    # Gọi trực tiếp chat_structured với session_factory test để bắt row ghi
    result = llm_client.chat_structured(
        "sys",
        "user đã sanitize",
        Classification,
        call_type=LlmCallType.classify,
        prompt_version=PROMPT_VERSION,
        feedback_id=fb_id,
        session_factory=TestSession,
    )
    assert isinstance(result, Classification)

    with TestSession() as db:
        rows = db.query(LlmCallLog).all()
        # 1 API call thành công → đúng 1 row
        assert len(rows) == 1
        row = rows[0]
        assert row.call_type is LlmCallType.classify
        assert row.prompt_version == PROMPT_VERSION
        assert row.model == get_settings().LLM_MODEL
        assert row.latency_ms >= 0
        assert row.prompt_tokens == 12
        assert row.completion_tokens == 34
        assert row.error is None
        assert row.feedback_id == fb_id


# ---------------------------------------------------------------------------
# Kill switch Langfuse (tiêu chí nghiệm thu phase 07)
# ---------------------------------------------------------------------------

def test_langfuse_kill_switch_disabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LANGFUSE_TRACING_ENABLED", False)
    assert tracing.get_langfuse() is None

    # trace wrapper phải no-op không raise khi kill-switch bật
    tracing.trace_llm_call(
        name="t",
        input_text_sanitized="text đã sanitize",
        output_summary="out",
        usage=None,
        latency_ms=1,
        model="m",
        prompt_version="v1",
    )


def test_langfuse_noop_when_keys_missing(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LANGFUSE_TRACING_ENABLED", True)
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "")
    assert tracing.get_langfuse() is None

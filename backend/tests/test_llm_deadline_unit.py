"""Unit — deadline tổng cho call provider (e2e 2026-11-05).

OpenRouter đệm keep-alive cho request non-streaming nên read-timeout của SDK không
kích hoạt; run UNDERSTAND kẹt >10 phút ở evaluator. Call vượt deadline phải trả
lỗi nhanh để fallback chain xử lý như provider error.
"""

import threading
import time
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.models.enums import LlmCallType
from app.services import llm_client


class _Out(BaseModel):
    ok: bool


def _hanging_client(release: threading.Event):
    def create(**kwargs):
        release.wait(5)  # mô phỏng provider treo (giải phóng ở teardown)
        raise RuntimeError("released")

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.fixture()
def hanging(monkeypatch):
    release = threading.Event()
    monkeypatch.setattr(llm_client, "_get_client", lambda: _hanging_client(release))
    monkeypatch.setattr(llm_client, "get_settings", lambda: SimpleNamespace(
        LLM_MODEL="m", LLM_MAX_TOKENS=10, LLM_CALL_DEADLINE_S=0.2,
        llm_model_for=lambda use_case: "m"))
    yield
    release.set()


def test_hung_provider_call_raises_deadline_quickly(hanging):
    t0 = time.perf_counter()
    with pytest.raises(llm_client.LLMDeadlineExceeded):
        llm_client._api_call([{"role": "user", "content": "x"}], None, "m")
    assert time.perf_counter() - t0 < 2


def test_chat_structured_turns_deadline_into_structure_error(hanging, monkeypatch):
    errors = []
    monkeypatch.setattr(llm_client, "_record_attempt", lambda **kw: errors.append(kw["error"]))
    t0 = time.perf_counter()
    with pytest.raises(llm_client.LLMStructureError):
        llm_client.chat_structured("s", "u", _Out, call_type=LlmCallType.evaluate, prompt_version="t")
    # Mode A + Mode B mỗi lượt ≤ deadline, rồi dừng (provider chết thì không retry)
    assert time.perf_counter() - t0 < 3
    assert len(errors) == 2 and all("LLMDeadlineExceeded" in e for e in errors)


def test_agent_call_types_get_tight_max_tokens(monkeypatch):
    """evaluate từng sinh lặp tới 8192 token (653 s) — call agent có trần riêng."""
    seen = []

    def fake_api(messages, response_format, model=None, max_tokens=None):
        seen.append(max_tokens)
        return '{"ok": true}', None

    monkeypatch.setattr(llm_client, "_api_call", fake_api)
    monkeypatch.setattr(llm_client, "_record_attempt", lambda **kw: None)
    for call_type in (LlmCallType.plan, LlmCallType.evaluate, LlmCallType.synthesize, LlmCallType.act_generate):
        llm_client.chat_structured("s", "u", _Out, call_type=call_type, prompt_version="t", model="m")
    assert seen == [1024, 1536, 2048, None]  # None → LLM_MAX_TOKENS chung

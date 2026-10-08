"""Plan 30 — model routing .env per use case.

Resolution chain: `MODEL_<USE_CASE>` → `LLM_MODEL`. `chat_structured` tự resolve
model từ `call_type` (map trung tâm) và truyền đúng model xuống `_api_call` +
`_record_attempt` — caller KHÔNG phải đổi.

Health payload phải expose map đã resolve để owner tự kiểm chứng routing.
"""

import pytest
from pydantic import BaseModel

from app.core.config import get_settings
from app.services import llm_client


USE_CASES = (
    "schema_map",
    "enrich",
    "taxonomy_generate",
    "topic_recommend",
    "cluster_name",
    "insight",
    "understand",
    "act",
)


class _Tiny(BaseModel):
    name: str


@pytest.fixture()
def routing_settings(monkeypatch):
    """Cô lập hoàn toàn khỏi backend/.env THẬT: mọi MODEL_* phải được set
    (rỗng = fallback) trước khi cache_clear — nếu không key nào không set sẽ
    đọc giá trị thật của .env làm test phụ thuộc môi trường."""
    monkeypatch.setenv("LLM_MODEL", "base/default-model")
    for uc in USE_CASES:
        monkeypatch.setenv(f"MODEL_{uc.upper()}", "")
    monkeypatch.setenv("MODEL_ENRICH", "cheap/enricher-model")
    monkeypatch.setenv("MODEL_TAXONOMY_GENERATE", "smart/gpt-model")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


# ---------------------------------------------------------------- resolution

def test_override_wins(routing_settings):
    assert routing_settings.llm_model_for("enrich") == "cheap/enricher-model"
    assert routing_settings.llm_model_for("taxonomy_generate") == "smart/gpt-model"


def test_fallback_global(routing_settings):
    for uc in ("insight", "understand", "act", "schema_map", "topic_recommend", "cluster_name"):
        assert routing_settings.llm_model_for(uc) == "base/default-model", uc


def test_unknown_use_case_falls_back(routing_settings):
    assert routing_settings.llm_model_for("khong_ton_tai") == "base/default-model"


def test_routing_map_covers_all(routing_settings):
    routing_map = routing_settings.model_routing_map
    assert set(routing_map) == set(USE_CASES)
    assert routing_map["enrich"] == "cheap/enricher-model"
    assert routing_map["understand"] == "base/default-model"


def test_enrich_engine_default(routing_settings):
    assert routing_settings.ENRICH_ENGINE == "llm"
    assert routing_settings.JEV_MODEL == "jev-latest"
    assert routing_settings.ENRICH_TOPIC_CONFIDENCE_FLOOR == pytest.approx(0.60)


# ------------------------------------------------- chat_structured propagation

class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def add(self, *args):
        pass

    def commit(self):
        pass

    def close(self):
        pass


def test_chat_structured_resolves_model_from_call_type(monkeypatch, routing_settings):
    captured: dict = {}

    def _fake_api_call(messages, response_format, model=None):
        captured["api_model"] = model
        return '{"name": "ok"}', {"prompt": 1, "completion": 1}

    def _fake_record(**kwargs):
        captured["record_model"] = kwargs.get("model")

    monkeypatch.setattr(llm_client, "_api_call", _fake_api_call)
    monkeypatch.setattr(llm_client, "_record_attempt", _fake_record)
    llm_client.chat_structured(
        "system",
        "user",
        _Tiny,
        call_type=llm_client.LlmCallType.schema_map,
        prompt_version="v1",
        session_factory=lambda: _FakeSession(),
    )
    assert captured["api_model"] == "base/default-model"
    assert captured["record_model"] == "base/default-model"


def test_chat_structured_uses_override_model(monkeypatch, routing_settings):
    captured: dict = {}

    def _fake_api_call(messages, response_format, model=None):
        captured["api_model"] = model
        return '{"name": "ok"}', None

    monkeypatch.setattr(llm_client, "_api_call", _fake_api_call)
    monkeypatch.setattr(llm_client, "_record_attempt", lambda **kwargs: None)
    llm_client.chat_structured(
        "system",
        "user",
        _Tiny,
        call_type=llm_client.LlmCallType.classify,  # → use case "enrich"
        prompt_version="v1",
        session_factory=lambda: _FakeSession(),
    )
    # classify/enrich cùng role — classify phải trúng MODEL_ENRICH override.
    assert captured["api_model"] == "cheap/enricher-model"


def test_chat_structured_enrich_call_type_routes(monkeypatch, routing_settings):
    """Regression 2026-10-07: call_type `enrich` (LlmCallType.enrich, plan 32)
    phải map sang use case `enrich` — thiếu key làm enrich ăn LLM_MODEL thay
    MODEL_ENRICH trong khi health map vẫn hiển thị đúng (lỗi thầm lặng)."""
    captured: dict = {}

    def _fake_api_call(messages, response_format, model=None):
        captured["api_model"] = model
        return '{"name": "ok"}', None

    monkeypatch.setattr(llm_client, "_api_call", _fake_api_call)
    monkeypatch.setattr(llm_client, "_record_attempt", lambda **kwargs: None)
    llm_client.chat_structured(
        "system",
        "user",
        _Tiny,
        call_type=llm_client.LlmCallType.enrich,
        prompt_version="v1",
        session_factory=lambda: _FakeSession(),
    )
    assert captured["api_model"] == "cheap/enricher-model"


def test_call_type_map_covers_all_enum_chat_values() -> None:
    """Mọi LlmCallType đi qua chat_structured phải có entry routing (embed là
    embedding, không qua chat — loại trừ)."""
    from app.models.enums import LlmCallType

    missing = [
        ct.value
        for ct in LlmCallType
        if ct.value not in llm_client._CALL_TYPE_USE_CASE and ct.value != "embed"
    ]
    assert missing == [], missing


# ------------------------------------------------------------------ health map

def test_health_exposes_routing_map(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["models"]) == set(USE_CASES)
    assert body["enrich_engine"] in ("llm", "jev")

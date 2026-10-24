"""Unit tests plan 32 — enricher v3 (finalize/UNCATEGORIZED/dispatch engine).

KHÔNG network, KHÔNG DB — đường llm mock ở tầng enricher (chat_structured),
đường jev mock ở tầng jev_client (systemone_enrich); threshold lấy từ settings
(monkeypatch env + cache_clear khi cần). Engine mặc định 'llm' qua autouse
fixture conftest (cô lập khỏi .env thật).
"""

import json

import pytest

from app.core.config import get_settings
from app.models.enums import LlmCallType
from app.schemas.enrichment import (
    EmotionScore,
    EnrichmentOut,
    TopicScore,
    strict_enrichment_schema,
)
from app.services import enricher
from app.services.llm_client import LLMStructureError

TAXONOMY = [("payment.payment_failure", "Payment failure", "Lỗi thanh toán"), ("support.response", "Support response", None)]


def _raw(**overrides) -> EnrichmentOut:
    base = dict(
        topics=[TopicScore(id="payment.payment_failure", probability=0.94)],
        sentiment="negative",
        emotions=[EmotionScore(label="frustration", probability=0.88)],
        intent="bug_report",
        severity="high",
        safety_issue=False,
        ai_issue=None,
        confidence=0.9,
        rationale="Lỗi thanh toán rõ ràng.",
    )
    base.update(overrides)
    return EnrichmentOut.model_validate(base)


# ------------------------------------------------------------------ finalize

def test_finalize_keeps_topics_above_floor() -> None:
    out = enricher.finalize_enrichment(
        _raw(topics=[
            TopicScore(id="payment.payment_failure", probability=0.94),
            TopicScore(id="support.response", probability=0.42),
        ]),
        taxonomy_version=2,
    )
    assert out["topics"] == ["payment.payment_failure"]
    assert out["uncategorized"] is False
    assert out["topic_confidence"] == pytest.approx(0.94)
    assert out["taxonomy_version"] == 2
    assert out["analysis_version"] == "enrich-v3"


def test_finalize_below_floor_becomes_uncategorized(monkeypatch) -> None:
    monkeypatch.setenv("ENRICH_TOPIC_CONFIDENCE_FLOOR", "0.95")
    get_settings.cache_clear()
    try:
        out = enricher.finalize_enrichment(
            _raw(topics=[TopicScore(id="payment.payment_failure", probability=0.70)]),
            taxonomy_version=1,
        )
    finally:
        get_settings.cache_clear()
    assert out["topics"] == []
    assert out["topic_scores"] == []
    assert out["topic_confidence"] is None
    assert out["uncategorized"] is True


def test_finalize_empty_topics_is_uncategorized() -> None:
    out = enricher.finalize_enrichment(_raw(topics=[]), taxonomy_version=1)
    assert out["uncategorized"] is True
    assert out["topics"] == []


def test_finalize_emotions_fallback_neutral() -> None:
    out = enricher.finalize_enrichment(_raw(emotions=[]), taxonomy_version=1)
    assert out["emotions"] == ["neutral"]


def test_finalize_keeps_multi_label_emotions() -> None:
    out = enricher.finalize_enrichment(
        _raw(emotions=[
            EmotionScore(label="frustration", probability=0.7),
            EmotionScore(label="anger", probability=0.6),
        ]),
        taxonomy_version=1,
    )
    assert out["emotions"] == ["frustration", "anger"]


# ------------------------------------------------------------- enrich_feedback

def test_enrich_feedback_prompt_uses_taxonomy_and_call_type(monkeypatch) -> None:
    captured: dict = {}

    def _fake_chat(system, user, schema, **kwargs):
        captured.update(system=system, user=user, kwargs=kwargs)
        assert schema is EnrichmentOut
        return _raw()

    monkeypatch.setattr(enricher, "chat_structured", _fake_chat)
    out = enricher.enrich_feedback(
        "text da sanitize", TAXONOMY, taxonomy_version=3, feedback_id="fb-1"
    )
    assert "payment.payment_failure — Payment failure (vi: Lỗi thanh toán)" in captured["user"]
    assert "support.response — Support response" in captured["user"]  # name_vi=None → không gloss
    assert "text da sanitize" in captured["user"]
    assert captured["kwargs"]["call_type"] is LlmCallType.enrich
    assert captured["kwargs"]["prompt_version"] == enricher.PROMPT_VERSION
    assert out["topics"] == ["payment.payment_failure"]


def test_enrich_feedback_dispatches_to_jev_engine(monkeypatch) -> None:
    """ENRICH_ENGINE=jev → systemone_enrich nhận đúng tham số, KHÔNG đụng chat."""
    monkeypatch.setenv("ENRICH_ENGINE", "jev")
    get_settings.cache_clear()
    captured: dict = {}
    sentinel = {"topics": [], "uncategorized": True}

    def _fake_systemone(text, labels, **kwargs):
        captured.update(text=text, labels=labels, kwargs=kwargs)
        return sentinel

    monkeypatch.setattr("app.services.jev_client.systemone_enrich", _fake_systemone)

    def _forbidden(*args, **kwargs):
        raise AssertionError("engine jev phải đi System One, không fallback chat")

    monkeypatch.setattr(enricher, "chat_structured", _forbidden)
    try:
        out = enricher.enrich_feedback(
            "text da sanitize",
            TAXONOMY,
            taxonomy_version=3,
            feedback_id="fb-1",
            analysis_run_id="run-1",
        )
    finally:
        get_settings.cache_clear()
    assert out is sentinel
    assert captured["text"] == "text da sanitize"
    assert captured["labels"] == TAXONOMY
    assert captured["kwargs"]["taxonomy_version"] == 3
    assert captured["kwargs"]["feedback_id"] == "fb-1"
    assert captured["kwargs"]["analysis_run_id"] == "run-1"


def test_enrich_feedback_jev_error_does_not_fallback_to_chat(monkeypatch) -> None:
    """LLMStructureError từ System One propagate nguyên vẹn — KHÔNG silent-fallback."""
    monkeypatch.setenv("ENRICH_ENGINE", "jev")
    get_settings.cache_clear()

    def _boom(*args, **kwargs):
        raise LLMStructureError("systemone HTTP 500.")

    monkeypatch.setattr("app.services.jev_client.systemone_enrich", _boom)

    def _forbidden(*args, **kwargs):
        raise AssertionError("không được fallback về chat")

    monkeypatch.setattr(enricher, "chat_structured", _forbidden)
    try:
        with pytest.raises(LLMStructureError, match="systemone"):
            enricher.enrich_feedback("text da sanitize", TAXONOMY)
    finally:
        get_settings.cache_clear()


def test_active_prompt_version_follows_engine(monkeypatch) -> None:
    monkeypatch.setenv("ENRICH_ENGINE", "jev")
    get_settings.cache_clear()
    assert enricher.active_prompt_version() == "jev-v1"
    monkeypatch.setenv("ENRICH_ENGINE", "llm")
    get_settings.cache_clear()
    assert enricher.active_prompt_version() == enricher.PROMPT_VERSION


# ----------------------------------------------------------------- strict A

def test_strict_schema_flat_no_refs() -> None:
    schema = strict_enrichment_schema()
    assert "$ref" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "topics", "sentiment", "emotions", "intent", "severity",
        "safety_issue", "ai_issue", "confidence", "rationale",
    }

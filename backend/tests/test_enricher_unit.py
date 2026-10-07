"""Unit tests plan 32 — enricher v3 (finalize/UNCATEGORIZED/batch coverage).

KHÔNG network, KHÔNG DB — chat_structured bị mock ở tầng enricher; threshold
lấy từ settings (monkeypatch env + cache_clear khi cần).
"""

import json
import uuid

import pytest

from app.core.config import get_settings
from app.models.enums import LlmCallType
from app.schemas.enrichment import (
    BatchEnrichmentOut,
    EmotionScore,
    EnrichmentOut,
    TopicScore,
    strict_enrichment_schema,
)
from app.services import enricher
from app.services.llm_client import LLMStructureError

TAXONOMY = [("payment.payment_failure", "Payment failure"), ("support.response", "Support response")]


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
    assert "payment.payment_failure — Payment failure" in captured["user"]
    assert "text da sanitize" in captured["user"]
    assert captured["kwargs"]["call_type"] is LlmCallType.enrich
    assert captured["kwargs"]["prompt_version"] == enricher.PROMPT_VERSION
    assert out["topics"] == ["payment.payment_failure"]


def test_enrich_batch_coverage_mismatch_raises(monkeypatch) -> None:
    fid = uuid.uuid4()

    def _fake_chat(system, user, schema, **kwargs):
        assert schema is BatchEnrichmentOut
        # Trả THIẾU một id so với request
        return BatchEnrichmentOut(items=[{"feedback_id": fid, "result": _raw()}])

    monkeypatch.setattr(enricher, "chat_structured", _fake_chat)
    with pytest.raises(LLMStructureError, match="IDs"):
        enricher.enrich_feedback_batch(
            [(fid, "a"), (uuid.uuid4(), "b")], taxonomy_labels=TAXONOMY
        )


def test_enrich_batch_finalizes_each_item(monkeypatch) -> None:
    fid1, fid2 = uuid.uuid4(), uuid.uuid4()

    def _fake_chat(system, user, schema, **kwargs):
        payload = json.loads(user.split("Feedback batch:\n")[1])
        assert [p["feedback_id"] for p in payload] == [str(fid1), str(fid2)]
        return BatchEnrichmentOut(items=[
            {"feedback_id": fid1, "result": _raw()},
            {"feedback_id": fid2, "result": _raw(topics=[])},
        ])

    monkeypatch.setattr(enricher, "chat_structured", _fake_chat)
    out = enricher.enrich_feedback_batch(
        [(fid1, "a"), (fid2, "b")], taxonomy_labels=TAXONOMY, taxonomy_version=4
    )
    assert out[fid1]["topics"] == ["payment.payment_failure"]
    assert out[fid2]["uncategorized"] is True
    assert out[fid2]["taxonomy_version"] == 4


# ----------------------------------------------------------------- strict A

def test_strict_schema_flat_no_refs() -> None:
    schema = strict_enrichment_schema()
    assert "$ref" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "topics", "sentiment", "emotions", "intent", "severity",
        "safety_issue", "ai_issue", "confidence", "rationale",
    }

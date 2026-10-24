"""Unit tests — jev_client System One per-item (owner 2026-10-22).

KHÔNG network: `_post_systemone` mock ở tầng module; `_record_attempt` mock để
bắt trace metadata. Wire format đối chiếu `scripts/spikes/s7_openrouter.py`
(endpoint `/systemone`, model `jev-latest`, answers Noul/Choice/Score).
"""

import httpx
import pytest

from app.core.config import get_settings
from app.models.enums import Emotion
from app.services import jev_client
from app.services.llm_client import LLMStructureError

TAXONOMY = [
    ("payment.payment_failure", "Payment failure", "Lỗi thanh toán"),
    ("support.response", "Support response", None),
]
SLUGS = [slug for slug, _, _ in TAXONOMY]

_EMOTION_NOUL = {"frustration": 0.75, "anger": 0.2, "delight": 0.2}


def _answers(**overrides):
    answers = {
        "sentiment": {"type": "choice", "choice": "negative", "probabilities": {"negative": 0.9, "positive": 0.02}},
        "intent": {"type": "choice", "choice": "bug_report", "probabilities": {"bug_report": 0.88}},
        "severity": {"type": "score", "score": 2.6, "probabilities": {"0": 0.03, "1": 0.05, "2": 0.07, "3": 0.85}},
        "safety": {"type": "noul", "noul": 0.3},
        "ai_issue": {"type": "choice", "choice": "none", "probabilities": {"none": 0.8}},
    }
    for slug in SLUGS:
        answers[f"topic::{slug}"] = {
            "type": "noul",
            "noul": 0.91 if slug == "payment.payment_failure" else 0.42,
        }
    for emo in Emotion:
        answers[f"emotion::{emo.value}"] = {"type": "noul", "noul": _EMOTION_NOUL.get(emo.value, 0.05)}
    answers.update(overrides)
    return answers


# ------------------------------------------------------------- build_questions

def test_build_questions_covers_closed_sets_and_taxonomy() -> None:
    questions = jev_client.build_questions(TAXONOMY)
    assert set(questions) == {
        "sentiment", "intent", "severity", "safety", "ai_issue",
        "topic::payment.payment_failure", "topic::support.response",
        *(f"emotion::{e.value}" for e in Emotion),
    }
    assert questions["severity"]["type"] == "score"
    assert questions["severity"]["criteria"] == ["low", "medium", "high", "critical"]
    assert questions["sentiment"]["type"] == "choice"
    assert questions["topic::payment.payment_failure"]["type"] == "noul"
    assert questions["ai_issue"]["criteria"]["none"] is not None


# --------------------------------------------------- answers_to_enrichment

def test_answers_map_to_enrichment_out() -> None:
    out = jev_client.answers_to_enrichment(_answers(), SLUGS)
    assert [t.id for t in out.topics] == ["payment.payment_failure", "support.response"]
    assert out.topics[0].probability == pytest.approx(0.91)
    assert out.sentiment.value == "negative"
    assert out.intent.value == "bug_report"
    assert out.safety_issue is False
    assert out.ai_issue is None
    assert out.confidence == pytest.approx(0.75, abs=1e-3)  # min = top emotion noul (safety KHÔNG tính)
    assert "JEV System One" in out.rationale


def test_severity_score_rounds_into_ladder() -> None:
    # score 2.6 → round = 3 → "critical" (thang 0..3, phương pháp S7)
    out = jev_client.answers_to_enrichment(_answers(), SLUGS)
    assert out.severity.value == "critical"


def test_ai_issue_choice_maps_to_enum() -> None:
    out = jev_client.answers_to_enrichment(
        _answers(ai_issue={"type": "choice", "choice": "hallucination", "probabilities": {"hallucination": 0.7}}),
        SLUGS,
    )
    assert out.ai_issue is not None and out.ai_issue.value == "hallucination"


def test_invalid_severity_score_raises() -> None:
    with pytest.raises(LLMStructureError, match="severity"):
        jev_client.answers_to_enrichment(_answers(severity={"type": "score", "score": 9, "probabilities": {}}), SLUGS)


def test_unknown_choice_raises() -> None:
    with pytest.raises(LLMStructureError, match="sentiment"):
        jev_client.answers_to_enrichment(
            _answers(sentiment={"type": "choice", "choice": "huge", "probabilities": {}}), SLUGS
        )


def test_missing_noul_raises() -> None:
    answers = _answers()
    del answers["safety"]
    with pytest.raises(LLMStructureError, match="safety"):
        jev_client.answers_to_enrichment(answers, SLUGS)


# ------------------------------------------------------------ systemone_enrich

def test_systemone_enrich_posts_state_and_questions(monkeypatch) -> None:
    captured: dict = {}

    def _fake_post(payload, *, endpoint, api_key):
        captured.update(payload=payload, endpoint=endpoint, api_key=api_key)
        return {"answers": _answers(), "model": "typesafe/jev-test", "usage": {"prompt_tokens": 1101, "completion_tokens": 395}}

    monkeypatch.setattr(jev_client, "_post_systemone", _fake_post)
    traced: list[dict] = []
    monkeypatch.setattr(jev_client, "_record_attempt", lambda **kw: traced.append(kw))

    out = jev_client.systemone_enrich(
        "text da sanitize", TAXONOMY, taxonomy_version=2, feedback_id="fb-1", analysis_run_id="run-1",
    )

    assert captured["payload"]["model"] == get_settings().JEV_MODEL
    assert captured["payload"]["state"] == "text da sanitize"  # PII boundary: caller sanitize trước
    assert set(captured["payload"]["questions"]) == set(jev_client.build_questions(TAXONOMY))
    assert captured["endpoint"].endswith("/systemone")
    assert out["topics"] == ["payment.payment_failure"]
    assert out["taxonomy_version"] == 2
    assert out["analysis_version"] == "enrich-v3"
    assert len(traced) == 1
    assert traced[0]["call_type"].value == "enrich"
    assert traced[0]["prompt_version"] == jev_client.JEV_PROMPT_VERSION
    assert traced[0]["usage"] == {"prompt": 1101, "completion": 395}
    assert traced[0]["error"] is None


def test_systemone_enrich_http_error_traces_then_raises(monkeypatch) -> None:
    def _fake_post(payload, *, endpoint, api_key):
        raise LLMStructureError("systemone HTTP 500.")

    monkeypatch.setattr(jev_client, "_post_systemone", _fake_post)
    traced: list[dict] = []
    monkeypatch.setattr(jev_client, "_record_attempt", lambda **kw: traced.append(kw))

    with pytest.raises(LLMStructureError, match="500"):
        jev_client.systemone_enrich("text da sanitize", TAXONOMY)
    assert len(traced) == 1
    assert "systemone HTTP 500." in traced[0]["error"]


# ------------------------------------------------------------- _post_systemone

class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.posts = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def close(self):
        pass

    def post(self, url, headers=None, json=None):
        self.posts += 1
        return self._responses.pop(0)


def test_post_systemone_retries_429_then_succeeds(monkeypatch) -> None:
    jev_client.close_client()
    client = _FakeClient([_FakeResponse(429), _FakeResponse(200, {"answers": {}})])
    monkeypatch.setattr(jev_client.httpx, "Client", lambda timeout: client)
    monkeypatch.setattr(jev_client.time, "sleep", lambda seconds: None)
    body = jev_client._post_systemone({}, endpoint="https://x/api/v1/systemone", api_key="k")
    assert body == {"answers": {}}
    assert client.posts == 2
    jev_client.close_client()


def test_post_systemone_transport_error_raises(monkeypatch) -> None:
    jev_client.close_client()
    class _DeadClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def close(self):
            pass

        def post(self, *a, **k):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(jev_client.httpx, "Client", lambda timeout: _DeadClient())
    with pytest.raises(LLMStructureError, match="transport"):
        jev_client._post_systemone({}, endpoint="https://x/systemone", api_key="k")
    jev_client.close_client()

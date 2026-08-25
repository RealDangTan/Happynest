"""Unit tests few-shot wiring (Phase 13 Task 5 stretch) — offline.

Mock chat_structured + embed seams; chỉ chứng minh runner ĐẨY khối "Ví dụ:"
vào prompt KHI env bật, và KHÔNG đẩy khi mặc định tắt.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.jobs import analysis_runner as runner_mod
from app.schemas.taxonomy import Classification
from app.services import classifier as classifier_mod


def _cls() -> Classification:
    return Classification.model_validate(
        dict(
            categories=["nhãn-test"],
            ai_issue=None,
            sentiment="neutral",
            severity="medium",
            safety_issue=False,
            confidence=0.9,
            rationale="ok",
        )
    )


class CaptureClassifier:
    def __init__(self):
        self.user_messages: list[str] = []

    def __call__(self, system, user, schema, **kwargs):
        self.user_messages.append(user)
        return _cls()


@pytest.fixture()
def wired_runner(monkeypatch):
    """Fake mọi seam ngoài LLM: few-shot loader + embedder + store_embedding."""
    captured = CaptureClassifier()
    monkeypatch.setattr(classifier_mod, "chat_structured", captured)
    monkeypatch.setattr(
        runner_mod,
        "_load_few_shot_examples",
        lambda db, limit=runner_mod.FEW_SHOT_LIMIT: [
            {"text": "ví dụ đã sanitize A", "label": {"categories": ["x"]}},
            {"text": "ví dụ đã sanitize B", "label": {"categories": []}},
        ],
    )
    monkeypatch.setattr(runner_mod, "embed_one", lambda text: [0.0] * 4)
    monkeypatch.setattr(runner_mod, "store_embedding", lambda db, fb, vec: None)

    run = SimpleNamespace(id=uuid.uuid4())
    fb = SimpleNamespace(
        id=uuid.uuid4(),
        raw_content="raw không bao giờ vào prompt",
        sanitized_content="feedback hiện tại đã sanitize",
        pii_detected=False,
        pii_entities=None,
        categories=None,
        ai_issue=None,
        sentiment=None,
        severity=None,
        confidence=None,
        safety_issue=False,
    )
    return {"captured": captured, "run": run, "fb": fb}


def test_fewshot_enabled_injects_example_block(monkeypatch, wired_runner):
    settings = get_settings()
    monkeypatch.setattr(settings, "CLASSIFY_FEWSHOT_ENABLED", True)
    runner_mod._process_item(None, wired_runner["run"], wired_runner["fb"])

    user_msg = wired_runner["captured"].user_messages[0]
    assert "Ví dụ:" in user_msg
    assert "ví dụ đã sanitize A" in user_msg
    assert "Feedback cần phân loại:" in user_msg
    # PII boundary: chỉ sanitized content vào prompt
    assert "raw không bao giờ vào prompt" not in user_msg


def test_fewshot_disabled_by_default_no_example_block(monkeypatch, wired_runner):
    settings = get_settings()
    monkeypatch.setattr(settings, "CLASSIFY_FEWSHOT_ENABLED", False)
    runner_mod._process_item(None, wired_runner["run"], wired_runner["fb"])

    user_msg = wired_runner["captured"].user_messages[0]
    assert "Ví dụ:" not in user_msg
    assert "Feedback cần phân loại:" in user_msg


def test_fewshot_labels_still_applied(monkeypatch, wired_runner):
    settings = get_settings()
    monkeypatch.setattr(settings, "CLASSIFY_FEWSHOT_ENABLED", True)
    fb = wired_runner["fb"]
    runner_mod._process_item(None, wired_runner["run"], fb)
    assert fb.categories == ["nhãn-test"]  # hành vi classify không đổi
    assert fb.review_status.value == "unreviewed"  # preset sạch → không pending

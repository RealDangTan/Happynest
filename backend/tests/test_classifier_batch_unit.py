import uuid

import pytest

from app.schemas.taxonomy import Classification
from app.services import classifier
from app.services.llm_client import LLMStructureError


def _classification() -> Classification:
    return Classification(
        categories=["quality"],
        ai_issue="inaccuracy",
        sentiment="negative",
        severity="medium",
        safety_issue=False,
        confidence=0.9,
        rationale="Kết quả sai.",
    )


def test_batch_classifier_returns_every_requested_id_once(monkeypatch) -> None:
    ids = [uuid.uuid4(), uuid.uuid4()]

    def fake_chat(*args, **kwargs):
        return classifier.BatchClassificationOut(
            items=[
                classifier.BatchClassificationItem(feedback_id=item_id, result=_classification())
                for item_id in reversed(ids)
            ]
        )

    monkeypatch.setattr(classifier, "chat_structured", fake_chat)
    result = classifier.classify_feedback_batch([(ids[0], "a"), (ids[1], "b")])

    assert list(result) == ids


def test_batch_classifier_rejects_missing_id(monkeypatch) -> None:
    ids = [uuid.uuid4(), uuid.uuid4()]

    monkeypatch.setattr(
        classifier,
        "chat_structured",
        lambda *args, **kwargs: classifier.BatchClassificationOut(
            items=[classifier.BatchClassificationItem(feedback_id=ids[0], result=_classification())]
        ),
    )

    with pytest.raises(LLMStructureError, match="IDs"):
        classifier.classify_feedback_batch([(ids[0], "a"), (ids[1], "b")])

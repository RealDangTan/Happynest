"""Enrichment schemas — output của JEV-role engine (plan 32; spec Listen
2026-10-07 §3–§6).

Closed-set tuyệt đối: topics CHỈ từ Active Taxonomy (slug), emotions/intent
theo enum khóa ở `app/models/enums.py`. `ai_issue`/`safety_issue` giữ lại trong
CÙNG call (chi phí ~0) vì HITL rule (severity/safety) và câu chuyện luận văn
(AI product) vẫn cần.

`strict_enrichment_schema()` = JSON schema PHẲNG cho Mode A (strict) — khuôn
`strict_classification_schema` + drift guard chết lúc import khi lệch.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AiIssue, Emotion, Intent, Sentiment, Severity

__all__ = [
    "TopicScore",
    "EmotionScore",
    "EnrichmentOut",
    "BatchEnrichmentItem",
    "BatchEnrichmentOut",
    "strict_enrichment_schema",
]


class TopicScore(BaseModel):
    """Một topic được chọn — `id` PHẢI là slug của node Active Taxonomy."""

    id: str = Field(min_length=1, max_length=200)
    probability: float = Field(ge=0.0, le=1.0)


class EmotionScore(BaseModel):
    label: Emotion
    probability: float = Field(ge=0.0, le=1.0)


class EnrichmentOut(BaseModel):
    """Raw output của engine TRƯỚC post-process (threshold/fallback neutral)
    — finalize xảy ra ở `services/enricher.finalize_enrichment`."""

    topics: list[TopicScore] = Field(default_factory=list, max_length=3)
    sentiment: Sentiment
    emotions: list[EmotionScore] = Field(default_factory=list, max_length=3)
    intent: Intent
    severity: Severity
    safety_issue: bool
    ai_issue: AiIssue | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=500)


class BatchEnrichmentItem(BaseModel):
    feedback_id: UUID
    result: EnrichmentOut


class BatchEnrichmentOut(BaseModel):
    items: list[BatchEnrichmentItem] = Field(min_length=1, max_length=10)


def _enum_values(py_enum: type) -> list[str]:
    return [m.value for m in py_enum]


_TOPIC_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "probability": {"type": "number"},
    },
    "required": ["id", "probability"],
    "additionalProperties": False,
}

_EMOTION_ITEM = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": _enum_values(Emotion)},
        "probability": {"type": "number"},
    },
    "required": ["label", "probability"],
    "additionalProperties": False,
}


def strict_enrichment_schema() -> dict:
    """JSON schema phẳng cho OpenAI strict structured output (Mode A)."""
    return {
        "type": "object",
        "properties": {
            "topics": {"type": "array", "items": _TOPIC_ITEM},
            "sentiment": {"type": "string", "enum": _enum_values(Sentiment)},
            "emotions": {"type": "array", "items": _EMOTION_ITEM},
            "intent": {"type": "string", "enum": _enum_values(Intent)},
            "severity": {"type": "string", "enum": _enum_values(Severity)},
            "safety_issue": {"type": "boolean"},
            "ai_issue": {
                "anyOf": [
                    {"type": "string", "enum": _enum_values(AiIssue)},
                    {"type": "null"},
                ]
            },
            "confidence": {"type": "number"},
            "rationale": {"type": "string"},
        },
        "required": [
            "topics",
            "sentiment",
            "emotions",
            "intent",
            "severity",
            "safety_issue",
            "ai_issue",
            "confidence",
            "rationale",
        ],
        "additionalProperties": False,
    }


def strict_batch_enrichment_schema() -> dict:
    """Schema phẳng cho BatchEnrichmentOut (không $ref — strict mode từ chối)."""
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "feedback_id": {"type": "string"},
                        "result": strict_enrichment_schema(),
                    },
                    "required": ["feedback_id", "result"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


_schema_keys = set(strict_enrichment_schema()["properties"])
_model_keys = set(EnrichmentOut.model_fields)
if _schema_keys != _model_keys:  # pragma: no cover — drift guard lúc import
    raise RuntimeError(
        f"enrichment drift: schema={sorted(_schema_keys)} vs model={sorted(_model_keys)}"
    )

"""Taxonomy phân loại — hợp đồng output của classifier (execute-plan §7, phase 07).

⚠️ Enums phải khớp TUYỆT ĐỐI bộ native PG enum của Phase 03 — nguồn duy nhất là
`app/models/enums.py`, module này chỉ re-export, KHÔNG định nghĩa lại.

`strict_classification_schema()` dựng JSON schema PHẲNG cho Mode A
(`response_format=json_schema`, strict) theo đúng hình dạng spike S2 đã chứng minh
provider honor 10/10: không `$defs`/`$ref`, enum inline, `additionalProperties=false`.
Giá trị enum lấy trực tiếp từ Python enum nên không thể trôi; guard import-time
so keys với `Classification.model_fields` để thêm/bớt field mà quên schema → chết sớm.
"""

from pydantic import BaseModel, Field

from app.models.enums import AiIssue, Sentiment, Severity  # noqa: F401 (re-export)

__all__ = [
    "AiIssue",
    "Sentiment",
    "Severity",
    "Classification",
    "strict_classification_schema",
]


class Classification(BaseModel):
    """Kết quả classify một feedback đã sanitize.

    Output ghi vào `feedback.ai_analysis` JSONB (reshape 2026-08-28 — không
    còn cột PG enum riêng; safety_issue nằm trong JSONB cùng các nhãn khác).
    """

    categories: list[str] = Field(min_length=1)
    ai_issue: AiIssue | None = None
    sentiment: Sentiment
    severity: Severity
    safety_issue: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=500)  # ≤ 2 câu — rubric ở system prompt


def _enum_values(py_enum: type) -> list[str]:
    return [m.value for m in py_enum]


def strict_classification_schema() -> dict:
    """JSON schema phẳng cho OpenAI strict structured output (Mode A).

    Tất cả field nằm trong `required` (bắt buộc bởi strict mode);
    `ai_issue` nullable qua anyOf với type null.
    """
    return {
        "type": "object",
        "properties": {
            "categories": {"type": "array", "items": {"type": "string"}},
            "ai_issue": {
                "anyOf": [
                    {"type": "string", "enum": _enum_values(AiIssue)},
                    {"type": "null"},
                ]
            },
            "sentiment": {"type": "string", "enum": _enum_values(Sentiment)},
            "severity": {"type": "string", "enum": _enum_values(Severity)},
            "safety_issue": {"type": "boolean"},
            "confidence": {"type": "number"},
            "rationale": {"type": "string"},
        },
        "required": [
            "categories",
            "ai_issue",
            "sentiment",
            "severity",
            "safety_issue",
            "confidence",
            "rationale",
        ],
        "additionalProperties": False,
    }


# Guard drift: schema tay phải phủ đúng tập field của model — lệch là bug code,
# chết ngay lúc import thay vì lỗi runtime giữa pipeline.
_schema_keys = set(strict_classification_schema()["properties"])
_model_keys = set(Classification.model_fields)
if _schema_keys != _model_keys:  # pragma: no cover — chỉ nổ khi sửa code lệch nhau
    raise RuntimeError(
        f"taxonomy drift: schema={sorted(_schema_keys)} vs model={sorted(_model_keys)}"
    )


# ---------------------------------------------------------------------------
# Governance (plan 23 — VoC OS §20–21)
# ---------------------------------------------------------------------------

from datetime import datetime  # noqa: E402
from uuid import UUID  # noqa: E402

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class TaxonomyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    parent_id: UUID | None
    name: str
    slug: str | None = None  # plan 31: topic id ổn định (bất biến khi rename)
    description: str | None
    kind: str
    status: str
    evidence_count: int
    first_seen: datetime | None
    last_seen: datetime | None
    created_at: datetime


class TaxonomyListOut(BaseModel):
    items: list[TaxonomyOut]
    total: int


class TaxonomyReviewActionIn(BaseModel):
    """POST /api/taxonomies/review/{id} — human quyết emerging theme (§21)."""

    action: str = Field(pattern="^(approve|merge|reject)$")
    merge_into_id: UUID | None = None  # bắt buộc khi action=merge
    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# GPT taxonomy proposal (plan 31 — spec Listen 2026-10-07 §2)
# ---------------------------------------------------------------------------

class ProposedTopic(BaseModel):
    """Một node trong proposal — PHẲNG, `parent` là NAME của topic khác trong
    list (None = root). Cố tình không dùng cây đệ quy: strict json_schema
    (Mode A) không cho `$ref`/recursion.

    Hierarchy 2–3 level do prompt ép; validate ở service khi apply."""

    name: str = Field(min_length=1, max_length=100)
    parent: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=300)


class TaxonomyProposalOut(BaseModel):
    """Output của GPT generate — proposal STATELESS (chưa đụng DB)."""

    topics: list[ProposedTopic] = Field(min_length=1, max_length=60)


def strict_taxonomy_proposal_schema() -> dict:
    """JSON schema phẳng cho Mode A của TaxonomyProposalOut (strict)."""
    topic_item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "parent": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["name", "parent", "description"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "topics": {"type": "array", "items": topic_item},
        },
        "required": ["topics"],
        "additionalProperties": False,
    }


class TaxonomyGenerateIn(BaseModel):
    """POST /api/taxonomies/generate — context tùy chọn bổ sung cho GPT."""

    product_id: UUID
    sample_size: int = Field(default=30, ge=1, le=50)
    product_type: str | None = Field(default=None, max_length=200)
    use_case: str | None = Field(default=None, max_length=500)
    persona: str | None = Field(default=None, max_length=300)


class TaxonomyGenerateOut(BaseModel):
    product_id: UUID
    sample_count: int
    proposal: TaxonomyProposalOut


class TaxonomyApplyIn(BaseModel):
    """POST /api/taxonomies/apply — human duyệt (có thể đã sửa) proposal."""

    product_id: UUID
    proposal: TaxonomyProposalOut


class TaxonomyApplyOut(BaseModel):
    created: list[TaxonomyOut]
    skipped: int
    taxonomy_version: int


# ---------------------------------------------------------------------------
# GPT topic recommendation (plan 34 — spec Listen §4): evolve từ pool
# uncategorized, human apply — KHÔNG per-record auto-emerging.
# ---------------------------------------------------------------------------

class TopicRecommendation(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent: str | None = Field(default=None, max_length=100)
    evidence_count: int = Field(ge=1)
    examples: list[str] = Field(default_factory=list, max_length=3)


class TopicRecommendationOut(BaseModel):
    """Empty pool → recommendations rỗng (min 0) — caller không tốn LLM."""

    recommendations: list[TopicRecommendation] = Field(default_factory=list, max_length=8)


class TopicRecommendIn(BaseModel):
    """POST /api/taxonomies/recommend — pm-only (tốn LLM)."""

    product_id: UUID
    pool_limit: int = Field(default=100, ge=10, le=200)


class TopicRecommendGenerateOut(BaseModel):
    product_id: UUID
    pool_count: int
    recommendations: list[TopicRecommendation]


class TopicRecommendApplyIn(BaseModel):
    """POST /api/taxonomies/recommend/apply — human chọn topic để nhận."""

    product_id: UUID
    topics: list[TopicRecommendation] = Field(min_length=1, max_length=8)


def strict_topic_recommendation_schema() -> dict:
    item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "parent": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "evidence_count": {"type": "integer"},
            "examples": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "parent", "evidence_count", "examples"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"recommendations": {"type": "array", "items": item}},
        "required": ["recommendations"],
        "additionalProperties": False,
    }


_rec_schema_keys = set(
    strict_topic_recommendation_schema()["properties"]["recommendations"]["items"][
        "properties"
    ]
)
_rec_model_keys = set(TopicRecommendation.model_fields)
if _rec_schema_keys != _rec_model_keys:  # pragma: no cover — drift guard
    raise RuntimeError(
        f"topic recommendation drift: schema={sorted(_rec_schema_keys)} "
        f"vs model={sorted(_rec_model_keys)}"
    )


_proposal_schema_keys = set(
    strict_taxonomy_proposal_schema()["properties"]["topics"]["items"]["properties"]
)
_proposal_model_keys = set(ProposedTopic.model_fields)
if _proposal_schema_keys != _proposal_model_keys:  # pragma: no cover — drift guard
    raise RuntimeError(
        f"taxonomy proposal drift: schema={sorted(_proposal_schema_keys)} "
        f"vs model={sorted(_proposal_model_keys)}"
    )

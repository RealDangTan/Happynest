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

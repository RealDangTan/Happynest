"""Query Compiler — validate mọi tool request theo Product Schema (VoC OS §29).

LLM chỉ gửi SEMANTIC tool request (field key + giá trị); compiler resolve
thành JSONB path và TỪ CHỐI field lạ — LLM không bao giờ viết SQL (guardrail
§68). Filter hỗ trợ:
- `topic`: containment trong `feedback.ai_analysis->'topics'` JSONB array.
- product field key (đã validate): `feedback.data->>'key' == value`.
- `source` / `severity` / `sentiment`: cột/ai_analysis chuẩn.
"""

import uuid

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.services import schema_registry


class UnknownFieldError(ValueError):
    """Field không có trong active product schema — tool trả về observation."""


def resolve_filters(
    db: Session, product_id: uuid.UUID, filters: dict | None
) -> list:
    """Dict filter → list SQLAlchemy conditions; field lạ → UnknownFieldError."""
    conditions: list = []
    if not filters:
        return conditions
    active = schema_registry.get_active_schema(db, product_id)
    known_keys = {f["key"] for f in schema_registry.schema_fields(active)}

    for key, value in filters.items():
        if key == "topic":
            conditions.append(Feedback.ai_analysis["topics"].contains([str(value)]))
        elif key == "severity":
            conditions.append(Feedback.ai_analysis["severity"].astext == str(value))
        elif key == "sentiment":
            conditions.append(Feedback.ai_analysis["sentiment"].astext == str(value))
        elif key == "source":
            conditions.append(Feedback.source == str(value))
        elif key in known_keys:
            conditions.append(Feedback.data[key].astext == str(value))
        else:
            raise UnknownFieldError(
                f"Field '{key}' không có trong product schema — "
                f"fields hợp lệ: {sorted(known_keys)}"
            )
    return conditions


def base_query(db: Session, product_id: uuid.UUID, filters: dict | None) -> Select:
    """SELECT ... FROM feedback WHERE product_id = :pid [AND filters]."""
    stmt = select(Feedback).where(Feedback.product_id == product_id)
    conditions = resolve_filters(db, product_id, filters)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt

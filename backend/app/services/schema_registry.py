"""Product Schema Registry — versioned, human-governed (VoC OS §8–9, plan 22).

Registry trả ACTIVE schema cho mapper/coverage/analytics; candidate version
chỉ được tạo qua Gate #1 (mapping decision). System core fields là HẰNG SỐ —
không bao giờ nằm trong definition JSONB, mapper vẫn thấy chúng như MAP target.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_schema import ProductSchema

#: VoC OS §9 — kernel ổn định mọi product đều có, không thuộc definition.
SYSTEM_CORE_FIELDS: list[dict] = [
    {
        "key": "feedback_text",
        "label": "Feedback Text",
        "description": "Nội dung phản hồi (bắt buộc, đã sanitize)",
        "type": "text",
    },
    {
        "key": "occurred_at",
        "label": "Occurred At",
        "description": "Thời điểm phản hồi diễn ra (ISO 8601)",
        "type": "datetime",
    },
    {
        "key": "source",
        "label": "Source",
        "description": "Nguồn phản hồi (app_review, survey, email...)",
        "type": "category",
    },
    {
        "key": "source_record_id",
        "label": "Source Record ID",
        "description": "ID dòng gốc trong nguồn (dedup/idempotency)",
        "type": "category",
    },
]

CORE_KEYS = {f["key"] for f in SYSTEM_CORE_FIELDS}

_FIELD_TYPES = {"category", "numeric", "datetime", "text", "boolean"}


def core_fields_for_llm() -> list[dict]:
    """Core fields dưới dạng các entry `existing_schema` cho mapper prompt."""
    return [dict(f, system_core=True) for f in SYSTEM_CORE_FIELDS]


def get_active_schema(db: Session, product_id: uuid.UUID) -> ProductSchema | None:
    """Version `active` hiện hành của product (None nếu chưa bootstrap)."""
    return db.scalars(
        select(ProductSchema)
        .where(ProductSchema.product_id == product_id, ProductSchema.status == "active")
        .order_by(ProductSchema.version.desc())
        .limit(1)
    ).first()


def list_versions(db: Session, product_id: uuid.UUID) -> list[ProductSchema]:
    return db.scalars(
        select(ProductSchema)
        .where(ProductSchema.product_id == product_id)
        .order_by(ProductSchema.version.desc())
    ).all()


def _validate_definition(definition: dict) -> None:
    fields = definition.get("fields")
    if not isinstance(fields, list):
        raise ValueError("definition.fields phải là list")
    keys: set[str] = set()
    for f in fields:
        if not isinstance(f, dict) or "key" not in f or "type" not in f:
            raise ValueError(f"field sai shape: {f!r}")
        if f["key"] in CORE_KEYS:
            raise ValueError(f"key '{f['key']}' thuộc system core — không được định nghĩa lại")
        if f["key"] in keys:
            raise ValueError(f"key trùng: '{f['key']}'")
        if f["type"] not in _FIELD_TYPES:
            raise ValueError(f"type không hợp lệ: {f['type']!r}")
        keys.add(f["key"])


def create_active_version(
    db: Session, product_id: uuid.UUID, definition: dict
) -> ProductSchema:
    """Tạo version MỚI và activate ngay (supersede version cũ) — 1 transaction.

    Chỉ gọi từ Gate #1 decision (human đã duyệt mapping/promote). Lệch shape →
    ValueError TRƯỚC khi đụng DB.
    """
    _validate_definition(definition)

    current = get_active_schema(db, product_id)
    next_version = (current.version + 1) if current else 1

    if current is not None:
        current.status = "superseded"
    schema = ProductSchema(
        product_id=product_id,
        version=next_version,
        definition=definition,
        status="active",
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


def schema_fields(schema: ProductSchema | None) -> list[dict]:
    """Fields của schema (definition.fields) — list rỗng khi chưa bootstrap."""
    if schema is None:
        return []
    return list(schema.definition.get("fields", []))

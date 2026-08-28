"""Pydantic schemas cho imports — plan 21 + LISTEN Gate #1 (plan 22)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ImportStatus


class ImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    source_type: str
    storage_path: str | None
    mapping_version: str | None
    schema_version: int | None
    status: ImportStatus
    row_count: int | None
    error: str | None
    created_at: datetime


class ImportListOut(BaseModel):
    items: list[ImportOut]
    total: int


# ------------------------------------------------------------------ LISTEN (plan 22)


class CandidateFieldIn(BaseModel):
    """Field mới đề xuất (LLM propose / human chỉnh) — VoC OS §10 PROMOTE."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,60}$")
    label: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    type: str = Field(pattern="^(category|numeric|datetime|text|boolean)$")


class MappingItemOut(BaseModel):
    """1 dòng proposal của LLM mapper (shape §11)."""

    source_field: str
    decision: str
    target: str | None = None
    candidate: CandidateFieldIn | None = None
    confidence: float
    reason: str
    needs_human_review: bool


class MappingProposalOut(BaseModel):
    """GET /api/imports/{id}/mapping — proposal đang chờ Gate #1."""

    mappings: list[MappingItemOut] = Field(min_length=1)


class MappingDecisionItem(BaseModel):
    """Quyết định human per source_field — Gate #1 (VoC OS §12).

    approve giữ nguyên proposal (AMBIGUOUS KHÔNG được approve); remap đổi
    target sang field hiện có; promote tạo field mới; demote → source_meta;
    ignore bỏ cột.
    """

    source_field: str
    action: str = Field(pattern="^(approve|remap|promote|demote|ignore)$")
    target_key: str | None = None
    candidate: CandidateFieldIn | None = None


class MappingDecisionIn(BaseModel):
    decisions: list[MappingDecisionItem] = Field(min_length=1)


class ImportApplyReport(BaseModel):
    """Response POST /api/imports/{id}/mapping/decision."""

    import_id: UUID
    imported: int
    failed: int
    errors: list[dict]
    schema_version: int | None


class FieldCoverageOut(BaseModel):
    """GET /api/products/{id}/schema/coverage — VoC OS §19."""

    total_records: int
    coverage: dict[str, float]


class ProductSchemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    version: int
    definition: dict[str, Any]
    status: str
    created_at: datetime


class ProductSchemaListOut(BaseModel):
    items: list[ProductSchemaOut]
    active_version: int | None

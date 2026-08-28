"""Pydantic schemas cho imports — plan 21."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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

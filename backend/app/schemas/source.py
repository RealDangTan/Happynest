"""Pydantic schemas cho sources registry — FE-03b (decisions 2026-08-25)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceIn(BaseModel):
    """Body POST /api/sources."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class SourceUpdate(BaseModel):
    """Body PATCH /api/sources/{id} — chỉ bật/tắt (không DELETE, xem migration)."""

    is_active: bool


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

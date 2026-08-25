"""Pydantic schemas cho clusters API — Phase 14 (contracts C1/C5)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClusterOut(BaseModel):
    """Một cụm trong GET /api/clusters — khớp C1 field-by-field."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    summary: str
    feedback_count: int
    first_seen: datetime
    last_seen: datetime
    current_count: int
    previous_count: int
    growth_ratio: float
    is_emerging: bool
    is_spike: bool
    suggested_priority: float | None
    # không nằm trên ORM — route điền sau model_validate (≤5 member mới nhất)
    sample_feedback_ids: list[UUID] = Field(default_factory=list)


class ClustersListOut(BaseModel):
    items: list[ClusterOut]


class ClusterRunOut(BaseModel):
    """Response POST /api/clusters/run — khớp C5."""

    clusters_upserted: int
    assigned_count: int
    unassigned_count: int
    duration_ms: int

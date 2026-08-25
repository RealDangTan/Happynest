"""Routes sources registry — FE-03b (docs/plans/FE-03b-source-columns-csv-map.md).

Registry NHẸ: GET/POST/PATCH toggle. KHÔNG validate ingest theo registry trong
đợt này (decisions 2026-08-25) — feedback vẫn ghi source string tự do.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.source import Source
from app.schemas.source import SourceIn, SourceOut, SourceUpdate

router = APIRouter(
    prefix="/api",
    tags=["sources"],
    # Cùng hàng rào với feedback: pm | operations.
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.get("/sources")
def list_sources(session: Session = Depends(get_db)) -> list[SourceOut]:
    """Trả TẤT CẢ (kể cả inactive — UI tự lọc và dùng flag để hiển thị)."""
    rows = session.scalars(select(Source).order_by(Source.name)).all()
    return [SourceOut.model_validate(r) for r in rows]


@router.post("/sources", status_code=status.HTTP_201_CREATED)
def create_source(
    item: SourceIn, session: Session = Depends(get_db)
) -> SourceOut:
    source = Source(name=item.name.strip(), description=item.description)
    session.add(source)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nguồn đã tồn tại.",
        )
    session.refresh(source)
    return SourceOut.model_validate(source)


@router.patch("/sources/{source_id}")
def update_source(
    source_id: uuid.UUID,
    item: SourceUpdate,
    session: Session = Depends(get_db),
) -> SourceOut:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Nguồn không tồn tại.")
    source.is_active = item.is_active
    session.commit()
    session.refresh(source)
    return SourceOut.model_validate(source)

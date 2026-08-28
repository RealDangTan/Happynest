"""Routes imports — LISTEN pipeline + Gate #1 (plan 22; VoC OS §6, §12).

POST /api/imports       : upload CSV → profile → LLM map → status=mapping_review
GET  /api/imports       : list
GET  /api/imports/{id}  : detail (status, storage_path, row_count...)
GET  /api/imports/{id}/mapping          : proposal đang chờ human
POST /api/imports/{id}/mapping/decision : Gate #1 → apply import (một lần)
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.import_ import Import
from app.schemas.import_ import (
    ImportApplyReport,
    ImportListOut,
    ImportOut,
    MappingDecisionIn,
    MappingProposalOut,
)
from app.services.import_service import (
    ImportStateError,
    apply_mapping_decision,
    get_proposal,
    start_import,
)

router = APIRouter(
    prefix="/api/imports",
    tags=["imports"],
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_import(
    file: UploadFile = File(...),
    product_id: uuid.UUID | None = Form(default=None),
    session: Session = Depends(get_db),
) -> ImportOut:
    """Upload CSV → profile + LLM mapping proposal (Gate #1 chờ human).

    409 nếu product đang có import dở mapping_review; 422 sai đuôi file;
    502 khi LLM mapper fail (import row đánh dấu failed).
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File phải có đuôi .csv.",
        )
    if product_id is None:
        from app.services.ingest_service import get_default_product

        try:
            product_id = get_default_product(session).id
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    raw = file.file.read()
    try:
        import_row = start_import(session, product_id, raw)
    except ImportStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — LLM/parse fail → 502, row đã failed
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mapping LLM thất bại: {type(exc).__name__}",
        )
    return ImportOut.model_validate(import_row)


@router.get("")
def list_imports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> ImportListOut:
    total = session.scalar(select(func.count()).select_from(Import))
    rows = session.scalars(
        select(Import).order_by(Import.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return ImportListOut(
        items=[ImportOut.model_validate(r) for r in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/{import_id}")
def get_import(import_id: uuid.UUID, session: Session = Depends(get_db)) -> ImportOut:
    import_row = session.get(Import, import_id)
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    return ImportOut.model_validate(import_row)


@router.get("/{import_id}/mapping")
def get_import_mapping(
    import_id: uuid.UUID, session: Session = Depends(get_db)
) -> MappingProposalOut:
    """Proposal mapping của import (Gate #1 input)."""
    import_row = session.get(Import, import_id)
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    try:
        return get_proposal(import_row)
    except ImportStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{import_id}/mapping/decision")
def decide_import_mapping(
    import_id: uuid.UUID,
    body: MappingDecisionIn,
    default_source: str | None = Query(default=None, max_length=100),
    session: Session = Depends(get_db),
) -> ImportApplyReport:
    """Gate #1 (VoC OS §12): human chốt mapping → import thực thi MỘT LẦN.

    Import đã applied/failed → 409; decision không phủ đủ source_field hoặc
    map không hợp lệ → 422; `?default_source=` dùng khi CSV không có cột source.
    """
    import_row = session.get(Import, import_id)
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    try:
        report = apply_mapping_decision(
            session, import_row, body.decisions, default_source=default_source
        )
    except ImportStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ImportApplyReport.model_validate(report)

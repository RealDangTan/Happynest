"""Routes imports — LISTEN pipeline + Gate #1 (plan 22; VoC OS §6, §12).

POST /api/imports       : upload CSV → deterministic profile → profile_ready
GET  /api/imports       : list
GET  /api/imports/{id}  : detail (status, storage_path, row_count...)
GET  /api/imports/{id}/mapping          : proposal đang chờ human
POST /api/imports/{id}/mapping/decision : Gate #1 → apply import (một lần)
"""

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.import_ import Import
from app.models.enums import ImportStatus
from app.models.user import User
from app.schemas.import_ import (
    ImportListOut,
    ImportOut,
    ImportPreviewOut,
    MappingDecisionIn,
    MappingProposalOut,
)
from app.services import import_service
from app.services.import_service import (
    ImportStateError,
    begin_mapping_decision,
    get_proposal,
    stage_import,
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
    """Upload CSV → sanitized deterministic profile. This is a free action."""
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
        import_row = stage_import(
            session,
            product_id,
            raw,
            original_filename=file.filename,
        )
    except ImportStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc), "message": "Product đang có import chưa hoàn tất."},
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return ImportOut.model_validate(import_row)


@router.get("")
def list_imports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_id: uuid.UUID | None = Query(default=None),
    statuses: list[ImportStatus] | None = Query(default=None, alias="status"),
    session: Session = Depends(get_db),
) -> ImportListOut:
    conditions = []
    if product_id is not None:
        conditions.append(Import.product_id == product_id)
    if statuses:
        conditions.append(Import.status.in_(statuses))
    attention_order = case(
        (Import.status.in_([
            ImportStatus.profile_ready,
            ImportStatus.mapping_review,
            ImportStatus.failed,
        ]), 0),
        (Import.status.in_([
            ImportStatus.mapping_generating,
            ImportStatus.importing,
        ]), 1),
        else_=2,
    )
    total = session.scalar(
        select(func.count()).select_from(Import).where(*conditions)
    )
    rows = session.scalars(
        select(Import)
        .where(*conditions)
        .order_by(attention_order, Import.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ImportListOut(
        items=[ImportOut.model_validate(r) for r in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/{import_id}/preview")
def get_import_preview(
    import_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> ImportPreviewOut:
    import_row = session.get(Import, import_id)
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    return ImportPreviewOut(
        id=import_row.id,
        original_filename=import_row.original_filename,
        source_row_count=import_row.source_row_count or 0,
        column_profiles=import_row.column_profiles or [],
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


@router.post("/{import_id}/mapping/proposal", status_code=202)
def propose_import_mapping(
    import_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> dict:
    """Explicit paid gate. A row lock prevents duplicate provider jobs."""
    import_row = session.scalar(
        select(Import).where(Import.id == import_id).with_for_update()
    )
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    try:
        import_service.begin_mapping_proposal(session, import_row)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "mapping_already_started", "message": str(exc)},
        )
    background_tasks.add_task(import_service.execute_mapping_background, import_row.id)
    return {"import_id": str(import_row.id), "status": "mapping_generating"}


@router.post("/{import_id}/cancel")
def cancel_import(
    import_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> ImportOut:
    import_row = session.scalar(
        select(Import).where(Import.id == import_id).with_for_update()
    )
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    try:
        import_service.cancel_import_file(import_row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    session.commit()
    session.refresh(import_row)
    return ImportOut.model_validate(import_row)


@router.post("/{import_id}/mapping/decision", status_code=202)
def decide_import_mapping(
    import_id: uuid.UUID,
    body: MappingDecisionIn,
    background_tasks: BackgroundTasks,
    default_source: str | None = Query(default=None, max_length=100),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Gate #1 (VoC OS §12): human chốt mapping → 202 NGAY, import chạy nền.

    Việc nạp rows (sanitize từng dòng — chậm với file lớn) chạy trong
    BackgroundTasks; FE poll `GET /api/imports/{id}` tới status imported/failed
    rồi đọc `report`. 409 khi import không ở mapping_review; 422 decision sai.
    """
    import_row = session.get(Import, import_id)
    if import_row is None:
        raise HTTPException(status_code=404, detail="Import không tồn tại.")
    try:
        final_map, meta_fields = begin_mapping_decision(session, import_row, body.decisions)
    except ImportStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # Decision memory (§52–53, plan 27) — log Gate #1 trước khi chạy nền
    from app.models.enums import DecisionSubject
    from app.services.decision_log import log_decision

    log_decision(
        session,
        product_id=import_row.product_id,
        subject_type=DecisionSubject.schema_mapping,
        subject_id=import_row.id,
        agent_value=import_row.mapping_proposal,
        human_value={"decisions": [d.model_dump() for d in body.decisions]},
        reviewer_id=user.id,
    )

    background_tasks.add_task(
        import_service.execute_import_background,
        import_row.id,
        final_map,
        meta_fields,
        default_source=default_source,
    )
    return {"import_id": str(import_row.id), "status": "importing"}

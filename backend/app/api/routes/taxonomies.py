"""Routes taxonomies — governance (plan 23; VoC OS §20–21).

GET  /api/taxonomies?product_id=         : tree (canonical + emerging, filter status)
GET  /api/taxonomies/review?product_id=  : hàng chờ emerging pending_review
POST /api/taxonomies/review/{id}         : Gate: approve | merge | reject
                                           — AI KHÔNG BAO GIỜ gọi endpoint này.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.schemas.taxonomy import (
    TaxonomyListOut,
    TaxonomyOut,
    TaxonomyReviewActionIn,
)
from app.services import taxonomy_service

router = APIRouter(
    prefix="/api/taxonomies",
    tags=["taxonomies"],
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.get("")
def list_taxonomies(
    product_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(
        default=None, pattern="^(active|pending_review|merged|rejected)$"
    ),
    session: Session = Depends(get_db),
) -> TaxonomyListOut:
    """Tree taxonomy của product; mặc định trả mọi status (FE tự dựng tree)."""
    conditions = [Taxonomy.product_id == product_id]
    if status_filter is not None:
        conditions.append(Taxonomy.status == status_filter)
    total = session.scalar(select(func.count()).select_from(Taxonomy).where(*conditions))
    rows = session.scalars(
        select(Taxonomy)
        .where(*conditions)
        .order_by(Taxonomy.kind, Taxonomy.evidence_count.desc(), Taxonomy.name)
    ).all()
    return TaxonomyListOut(
        items=[TaxonomyOut.model_validate(r) for r in rows],
        total=int(total or 0),
    )


@router.get("/review")
def review_queue(
    product_id: uuid.UUID = Query(...),
    session: Session = Depends(get_db),
) -> TaxonomyListOut:
    """Hàng chờ emerging theme chờ human review (§21 — accumulate evidence)."""
    rows = session.scalars(
        select(Taxonomy)
        .where(
            Taxonomy.product_id == product_id,
            Taxonomy.status == "pending_review",
        )
        .order_by(Taxonomy.evidence_count.desc(), Taxonomy.first_seen)
    ).all()
    return TaxonomyListOut(
        items=[TaxonomyOut.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post("/review/{taxonomy_id}")
def review_theme(
    taxonomy_id: uuid.UUID,
    body: TaxonomyReviewActionIn,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaxonomyOut:
    """Human quyết một emerging theme — approve/merge/reject (§21 flow)."""
    theme = session.get(Taxonomy, taxonomy_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="Taxonomy node không tồn tại.")
    if theme.kind != "emerging" or theme.status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node đang là {theme.kind}/{theme.status} — không ở hàng chờ review.",
        )

    agent_value = {
        "name": theme.name,
        "kind": theme.kind,
        "status": theme.status,
        "evidence_count": theme.evidence_count,
    }

    if body.action == "approve":
        result = TaxonomyOut.model_validate(taxonomy_service.approve_theme(session, theme))
    elif body.action == "reject":
        result = TaxonomyOut.model_validate(taxonomy_service.reject_theme(session, theme))
    else:
        if body.merge_into_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="action=merge yêu cầu merge_into_id.",
            )
        target = session.get(Taxonomy, body.merge_into_id)
        if target is None or target.product_id != theme.product_id:
            raise HTTPException(status_code=404, detail="Merge target không tồn tại.")
        if target.id == theme.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không merge node vào chính nó.",
            )
        result = TaxonomyOut.model_validate(
            taxonomy_service.merge_theme(session, theme, target)
        )

    # Decision memory (§52–53, plan 27)
    from app.models.enums import DecisionSubject
    from app.services.decision_log import log_decision

    log_decision(
        session,
        product_id=theme.product_id,
        subject_type=DecisionSubject.taxonomy,
        subject_id=theme.id,
        agent_value=agent_value,
        human_value={"action": body.action, "merge_into_id": str(body.merge_into_id) if body.merge_into_id else None},
        reason=body.reason,
        reviewer_id=user.id,
    )
    return result

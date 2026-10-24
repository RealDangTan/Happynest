"""Routes taxonomies — governance (plan 23; VoC OS §20–21) + GPT proposal
(plan 31; spec Listen 2026-10-07).

GET  /api/taxonomies?product_id=         : tree (canonical + emerging, filter status)
GET  /api/taxonomies/review?product_id=  : hàng chờ emerging pending_review (legacy)
POST /api/taxonomies/review/{id}         : Gate: approve | merge | reject
                                           — AI KHÔNG BAO GIỜ gọi endpoint này.
POST /api/taxonomies/generate            : GPT sinh proposal (tốn LLM)
POST /api/taxonomies/apply               : HUMAN apply proposal → Active Taxonomy
                                           — AI KHÔNG BAO GIỜ gọi endpoint này.
POST /api/taxonomies/recommend           : GPT đề xuất topic từ pool uncategorized
POST /api/taxonomies/recommend/apply     : HUMAN nhận topic đề xuất → Taxonomy v2
POST /api/taxonomies/nodes               : HUMAN tạo node thủ công (owner 2026-10-23)
PATCH /api/taxonomies/nodes/{slug}       : HUMAN đổi tên (EN canonical) / name_vi (hiển thị) / mô tả
                                           (slug bất biến)
DELETE /api/taxonomies/nodes/{slug}      : HUMAN xóa node lá (còn con → 409)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    product_or_404,
)
from app.models.enums import DecisionSubject
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.schemas.taxonomy import (
    ProposedTopic,
    TaxonomyApplyIn,
    TaxonomyApplyOut,
    TaxonomyGenerateIn,
    TaxonomyGenerateOut,
    TaxonomyListOut,
    TaxonomyNodeCreateIn,
    TaxonomyNodeUpdateIn,
    TaxonomyOut,
    TaxonomyProposalOut,
    TaxonomyReviewActionIn,
    TopicRecommendApplyIn,
    TopicRecommendGenerateOut,
    TopicRecommendIn,
)
from app.services import taxonomy_service
from app.services.decision_log import log_decision
from app.services.taxonomy_service import (
    TaxonomyConflictError,
    TaxonomyValidationError,
)

router = APIRouter(
    prefix="/api/taxonomies",
    tags=["taxonomies"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def list_taxonomies(
    product_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(
        default=None, pattern="^(active|pending_review|merged|rejected)$"
    ),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaxonomyListOut:
    """Tree taxonomy của product; mặc định trả mọi status (FE tự dựng tree)."""
    product_or_404(session, product_id, current_user)
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
    current_user: User = Depends(get_current_user),
) -> TaxonomyListOut:
    """Hàng chờ emerging theme chờ human review (§21 — accumulate evidence)."""
    product_or_404(session, product_id, current_user)
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
    product_or_404(session, theme.product_id, user)
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


@router.post("/generate")
def generate_taxonomy(
    body: TaxonomyGenerateIn,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaxonomyGenerateOut:
    """GPT sinh proposal taxonomy từ sample PHÂN TẦNG theo thời gian (đã
    sanitize, gộp trùng lặp) + context. Proposal STATELESS; chỉ `apply` đụng
    DB. Product chưa có feedback → 422 (không đốt LLM call)."""
    product = product_or_404(session, body.product_id, current_user)
    context = {
        "product_type": body.product_type,
        "use_case": body.use_case,
        "persona": body.persona,
    }
    try:
        proposal, sample_count = taxonomy_service.generate_proposal(
            session, product, sample_size=body.sample_size, context=context
        )
    except TaxonomyValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return TaxonomyGenerateOut(
        product_id=product.id, sample_count=sample_count, proposal=proposal
    )


@router.post("/apply")
def apply_taxonomy(
    body: TaxonomyApplyIn,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaxonomyApplyOut:
    """HUMAN gate: apply proposal (có thể đã sửa generate/recommend) → tạo
    node canonical/active + bump taxonomy_version + decision memory."""
    product = product_or_404(session, body.product_id, user)
    try:
        result = taxonomy_service.apply_proposal(session, product, body.proposal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Decision memory: 1 dòng per node TẠO MỚI (khớp pattern review — per node).
    from app.models.enums import DecisionSubject
    from app.services.decision_log import log_decision

    for node in result["created"]:
        log_decision(
            session,
            product_id=product.id,
            subject_type=DecisionSubject.taxonomy,
            subject_id=node.id,
            agent_value={"name": node.name, "slug": node.slug, "source": "proposal_apply"},
            human_value={"applied": True, "taxonomy_version": result["taxonomy_version"]},
            reviewer_id=user.id,
        )
    return TaxonomyApplyOut(
        created=[TaxonomyOut.model_validate(n) for n in result["created"]],
        skipped=result["skipped"],
        taxonomy_version=result["taxonomy_version"],
    )


@router.post("/recommend")
def recommend_topics(
    body: TopicRecommendIn,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicRecommendGenerateOut:
    """Plan 34 — GPT đọc pool uncategorized/low-confidence → đề xuất topic mới
    (STATELESS). Pool rỗng → recommendations rỗng, không gọi LLM."""
    product = product_or_404(session, body.product_id, current_user)
    result, pool_count = taxonomy_service.recommend_topics(
        session, product, pool_limit=body.pool_limit
    )
    return TopicRecommendGenerateOut(
        product_id=product.id, pool_count=pool_count, recommendations=result.recommendations
    )


@router.post("/recommend/apply")
def apply_recommended_topics(
    body: TopicRecommendApplyIn,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaxonomyApplyOut:
    """HUMAN gate: nhận topic đề xuất → tạo canonical/active (tái dùng
    apply_proposal: idempotent + bump version + decision memory)."""
    product = product_or_404(session, body.product_id, user)
    proposal = TaxonomyProposalOut(
        topics=[
            ProposedTopic(name=t.name, name_vi=t.name_vi, parent=t.parent, description=None)
            for t in body.topics
        ]
    )
    try:
        result = taxonomy_service.apply_proposal(session, product, proposal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    from app.models.enums import DecisionSubject
    from app.services.decision_log import log_decision

    for node in result["created"]:
        log_decision(
            session,
            product_id=product.id,
            subject_type=DecisionSubject.taxonomy,
            subject_id=node.id,
            agent_value={"name": node.name, "slug": node.slug, "source": "topic_recommendation"},
            human_value={"applied": True, "taxonomy_version": result["taxonomy_version"]},
            reviewer_id=user.id,
        )
    return TaxonomyApplyOut(
        created=[TaxonomyOut.model_validate(n) for n in result["created"]],
        skipped=result["skipped"],
        taxonomy_version=result["taxonomy_version"],
    )


@router.post("/nodes", status_code=201)
def create_taxonomy_node(
    body: TaxonomyNodeCreateIn,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaxonomyOut:
    """HUMAN CRUD (owner 2026-10-23): tự tay thêm chủ đề vào Active Taxonomy —
    slug tự sinh theo plan 31, bump taxonomy_version (tập nhãn đóng đổi)."""
    product = product_or_404(session, body.product_id, user)
    try:
        node = taxonomy_service.create_manual_node(
            session,
            product,
            name=body.name,
            parent_slug=body.parent_slug,
            description=body.description,
            name_vi=body.name_vi,
        )
    except TaxonomyValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except TaxonomyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    log_decision(
        session,
        product_id=product.id,
        subject_type=DecisionSubject.taxonomy,
        subject_id=node.id,
        agent_value=None,
        human_value={
            "action": "manual_create",
            "name": node.name,
            "slug": node.slug,
            "parent_slug": body.parent_slug,
        },
        reviewer_id=user.id,
    )
    return TaxonomyOut.model_validate(node)


@router.patch("/nodes/{taxonomy_slug}")
def update_taxonomy_node(
    taxonomy_slug: str,
    body: TaxonomyNodeUpdateIn,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaxonomyOut:
    """HUMAN CRUD: đổi tên canonical (EN) / tên hiển thị (name_vi) / mô tả.
    Slug BẤT BIẾN (plan 31) — không bump version vì tập nhãn không đổi.
    description=None là XÓA mô tả; name_vi=None là GIỮ nguyên hiển thị."""
    product = product_or_404(session, body.product_id, user)
    if body.name is None and body.description is None and body.name_vi is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cần ít nhất một trong các trường name / name_vi / description.",
        )
    try:
        node = taxonomy_service.update_manual_node(
            session,
            product,
            slug=taxonomy_slug,
            name=body.name,
            description=body.description,
            name_vi=body.name_vi,
        )
    except TaxonomyValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except TaxonomyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if node is None:
        raise HTTPException(status_code=404, detail="Chủ đề không tồn tại.")

    log_decision(
        session,
        product_id=product.id,
        subject_type=DecisionSubject.taxonomy,
        subject_id=node.id,
        agent_value={"name": node.name, "slug": node.slug},
        human_value={"action": "manual_update", "name": body.name, "description": body.description},
        reviewer_id=user.id,
    )
    return TaxonomyOut.model_validate(node)


@router.delete("/nodes/{taxonomy_slug}", status_code=204)
def delete_taxonomy_node(
    taxonomy_slug: str,
    product_id: uuid.UUID = Query(...),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """HUMAN CRUD: xóa node lá khỏi Active Taxonomy. Node còn con → 409.
    Dữ liệu đã enrich giữ nguyên slug (FE hiển thị fallback) — chỉ tập nhãn
    ĐÓNG tương lai thu hẹp; bump taxonomy_version."""
    product = product_or_404(session, product_id, user)
    try:
        node = taxonomy_service.delete_manual_node(session, product, slug=taxonomy_slug)
    except TaxonomyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if node is None:
        raise HTTPException(status_code=404, detail="Chủ đề không tồn tại.")

    log_decision(
        session,
        product_id=product.id,
        subject_type=DecisionSubject.taxonomy,
        subject_id=node.id,
        agent_value={"name": node.name, "slug": node.slug},
        human_value={"action": "manual_delete"},
        reviewer_id=user.id,
    )

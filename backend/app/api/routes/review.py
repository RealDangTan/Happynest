"""Routes HITL — Phase 13 (13-hitl-langgraph.md §3.4).

POST /api/reviews/{feedback_id}      — approve | edit | reject qua graph LangGraph
POST /api/corrections/{feedback_id}  — sửa nhãn trực tiếp (thuần DB, KHÔNG graph)

Guard role pm|operations gắn ở TẦNG ROUTER (y hệt routes/feedback.py).
Bộ lỗi chuẩn C3: 404 thiếu row · 409 trạng thái không hợp lệ · 422 body sai
(FastAPI tự trả từ schema validators) · 401/403 auth.

⚠️ PII boundary: mọi response đi qua FeedbackOut/CorrectionOut — không có
raw_content; corrections chỉ nhận nhãn, không nhận text.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.enums import ReviewAction, ReviewStatus
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackOut
from app.schemas.hitl import CorrectionIn, CorrectionOut, ReviewIn
from app.services import hitl_graph

router = APIRouter(
    prefix="/api",
    tags=["hitl"],
    # Guard toàn router: chỉ pm | operations được duyệt/sửa feedback.
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("/reviews/{feedback_id}", response_model=FeedbackOut)
def submit_review(
    feedback_id: uuid.UUID,
    body: ReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("pm", "operations")),
) -> FeedbackOut:
    """Duyệt/sửa/từ chối feedback đang `pending` — resume graph HITL.

    Graph tự lo interrupt/resume + checkpoint (sống sót restart). Response là
    FeedbackOut SAU cập nhật (review_status → approved/edited/rejected).
    """
    fb = db.get(Feedback, feedback_id)
    if fb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feedback không tồn tại.")
    # Pre-check hàng chờ: chỉ chặn row CHƯA BAO GIỜ vào graph ('unreviewed').
    # Row đã rời 'pending' (approved/edited/rejected) VẪN được đưa vào graph:
    # thread completed → graph raise ReviewAlreadyCompleted → 409 y như cũ;
    # thread đang dở vì crash giữa apply_action-commit và record_correction-
    # commit → request này chính là cơ chế TỰ-HEAL: chạy nốt phần còn thiếu
    # thay vì kẹt 409 vĩnh viễn và đánh mất dòng log (decisions.md 2026-08-25).
    if fb.review_status == ReviewStatus.unreviewed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Feedback đang '{fb.review_status.value}' — không nằm trong hàng chờ review.",
        )
    try:
        hitl_graph.submit_review(
            feedback_id,
            user.id,
            {
                "action": body.action,
                "edited_content": body.edited_content,
                "reason": body.reason,
            },
        )
    except hitl_graph.ReviewAlreadyCompleted as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except hitl_graph.CheckpointUnavailable as exc:
        # Supabase chập chờn lúc dựng bảng checkpoint — client retry sau.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    db.refresh(fb)
    return FeedbackOut.model_validate(fb)


@router.post("/corrections/{feedback_id}", response_model=CorrectionOut)
def submit_correction(
    feedback_id: uuid.UUID,
    body: CorrectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("pm", "operations")),
) -> CorrectionOut:
    """Sửa nhãn feedback ĐÃ CLASSIFY — thao tác thuần DB, không phụ thuộc
    review_status (đúng C3), nuôi few-shot loop cho classifier."""
    fb = db.get(Feedback, feedback_id)
    if fb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feedback không tồn tại.")
    # Marker "chưa classify" theo quy ước runner: categories IS NULL.
    if fb.categories is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Feedback chưa classify (categories NULL) — không có nhãn để sửa.",
        )

    original_snapshot = hitl_graph.snapshot_of(fb)
    for field, value in body.label_updates().items():
        setattr(fb, field, value)

    # corrected_value cho few-shot: nhãn SAU sửa, enum về value thuần để JSONB sạch
    corrected_enums: dict = {}
    for key in ("categories", "ai_issue", "severity", "sentiment"):
        v = getattr(fb, key)
        corrected_enums[key] = (
            [item for item in v] if key == "categories" and v is not None else v
        )
        if hasattr(v, "value"):
            corrected_enums[key] = v.value

    from app.models.correction_example import CorrectionExample
    from app.models.human_review import HumanReview

    db.add(
        HumanReview(
            feedback_id=fb.id,
            original_value=original_snapshot,
            edited_value=hitl_graph.snapshot_of(fb),
            action=ReviewAction.edit,
            reason=body.note,
            reviewer_id=user.id,
        )
    )
    db.add(
        CorrectionExample(
            feedback_id=fb.id,
            original_prediction=original_snapshot,
            corrected_value=corrected_enums,
            reason=body.note,
        )
    )
    db.commit()
    db.refresh(fb)
    out = CorrectionOut.model_validate(fb)
    return out.model_copy(update={"correction_recorded": True})

"""Routes actions — ACT layer + Gate #3 (plan 26; VoC OS §44–52).

POST  /api/insights/{id}/actions/generate : LLM routing + candidates + estimates
GET   /api/insights/{id}/actions          : portfolio + priority matrix (§50)
POST  /api/insights/{id}/actions          : human thêm action
PATCH /api/actions/{action_id}            : Gate #3 override (human_*) + recompute
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.action import Action
from app.models.enums import BusinessFunction
from app.models.insight import Insight
from app.schemas.action import (
    ActionGenerateOut,
    ActionsListOut,
    ActionOut,
    ActionUpdateIn,
    HumanActionIn,
)
from app.services import act_agent

router = APIRouter(
    prefix="/api",
    tags=["actions"],
    dependencies=[Depends(require_role("pm", "operations"))],
)


def _load_insight(db: Session, insight_id: uuid.UUID) -> Insight:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight không tồn tại.")
    return insight


def _matrix(items: list[Action]) -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {
        "quick_wins": [],
        "strategic_investments": [],
        "low_priority": [],
        "reconsider": [],
    }
    for a in items:
        impact, effort, _, _ = act_agent.effective_scores(a)
        matrix[act_agent.matrix_quadrant(impact, effort)].append(str(a.id))
    return matrix


@router.post("/insights/{insight_id}/actions/generate")
def generate_actions(
    insight_id: uuid.UUID, db: Session = Depends(get_db)
) -> ActionGenerateOut:
    """Sinh action portfolio từ insight ĐÃ DUYỆT — 409 nếu insight pending/rejected."""
    insight = _load_insight(db, insight_id)
    if insight.status not in ("approved", "edited"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insight đang '{insight.status}' — ACT chỉ chạy trên insight đã duyệt (§44).",
        )
    created, skipped_functions = act_agent.generate_actions(db, insight)
    return ActionGenerateOut(
        actions_created=len(created), functions_skipped=sorted(skipped_functions)
    )


@router.get("/insights/{insight_id}/actions")
def list_actions(
    insight_id: uuid.UUID, db: Session = Depends(get_db)
) -> ActionsListOut:
    _load_insight(db, insight_id)
    items = db.scalars(
        select(Action)
        .where(Action.insight_id == insight_id)
        .order_by(Action.priority_score.desc())
    ).all()
    return ActionsListOut(
        items=[ActionOut.model_validate(a) for a in items],
        matrix=_matrix(list(items)),
    )


@router.post("/insights/{insight_id}/actions", status_code=status.HTTP_201_CREATED)
def add_human_action(
    insight_id: uuid.UUID, body: HumanActionIn, db: Session = Depends(get_db)
) -> ActionOut:
    """Human tự thêm action — priority tính bằng cùng công thức deterministic."""
    _load_insight(db, insight_id)
    action = Action(
        insight_id=insight_id,
        function=body.function,
        recommendation=body.recommendation,
        rationale=body.rationale or "",
        impact=body.impact,
        effort=body.effort,
        urgency=body.urgency,
        confidence=1.0,
        priority_score=0.0,
        status="accepted",
    )
    act_agent.recompute_priority(action)
    db.add(action)
    db.commit()
    db.refresh(action)
    return ActionOut.model_validate(action)


@router.patch("/actions/{action_id}")
def update_action(
    action_id: uuid.UUID, body: ActionUpdateIn, db: Session = Depends(get_db)
) -> ActionOut:
    """Gate #3: human edit scores/action — agent values giữ nguyên (§52)."""
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action không tồn tại.")

    touched_scores = False
    if body.impact is not None:
        action.human_impact = body.impact
        touched_scores = True
    if body.effort is not None:
        action.human_effort = body.effort
        touched_scores = True
    if body.urgency is not None:
        action.human_urgency = body.urgency
        touched_scores = True
    if touched_scores:
        act_agent.recompute_priority(action)
    if body.recommendation is not None:
        action.recommendation = body.recommendation
    if body.rationale is not None:
        action.rationale = body.rationale
    if body.override_reason is not None:
        action.override_reason = body.override_reason
    if body.status is not None:
        action.status = body.status
    elif action.status == "proposed":
        action.status = "edited"
    db.commit()
    db.refresh(action)
    return ActionOut.model_validate(action)

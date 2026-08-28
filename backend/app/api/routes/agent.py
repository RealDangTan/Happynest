"""Routes agent — tạo run, theo dõi, quyết định HITL (phase 19 Task 4).

⚠️ Hành vi đã ghi api-checklist: POST /runs KHÔNG replace-all — chạy khi run
cũ đang running vẫn hợp lệ (insight mới insert thêm, không xoá insight cũ,
khác runner deterministic). Decision trên thread completed → 409; thread
crash-dở-dâng sau interrupt → resume tự heal (chạy nốt graph, mirror phase 13).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.db.session import SessionLocal
from app.jobs.agent_runner import (
    CheckpointUnavailable,
    get_thread_state,
    resume_with_decision,
    select_targets,
    start_agent_run,
)
from app.models.action_draft import ActionDraft
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.models.insight import Insight
from app.schemas.agent import AgentDecisionIn, AgentRunCreatedOut, AgentRunStatusOut
from app.services.hitl_graph import ReviewAlreadyCompleted
from happynest_agent.graph import snapshot_payload, thread_phase

router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
    # Guard toàn router — job tốn tiền LLM tokens + quyền quyết insight.
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("/runs")
def create_agent_run(db: Session = Depends(get_db)) -> AgentRunCreatedOut:
    """Tạo agent run + spawn thread nền; trả NGAY run_id + targets đã chọn.

    Targets rỗng → run completed ngay với note trong `error` (client thấy kết
    quả dứt khoát, xem agent_runner.start_agent_run)."""
    targets = select_targets(db)
    run = start_agent_run(db, targets=targets)
    return AgentRunCreatedOut(run_id=run.id, targets=targets)


def _llm_calls_used(run_id: uuid.UUID) -> int | None:
    from happynest_agent.nodes import _llm_calls_used

    try:
        with SessionLocal() as db:
            return _llm_calls_used(db, run_id)
    except Exception:  # noqa: BLE001 — thống kê phụ, không chết response
        return None


@router.get("/runs/{run_id}")
def get_agent_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentRunStatusOut:
    """Trạng thái run: phần tĩnh từ row AnalysisRun, phần động từ snapshot
    checkpoint (steps_used/targets/insights_created/pending_approval)."""
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Run không tồn tại.")

    from app.core.config import get_settings

    out = AgentRunStatusOut(
        run_id=run.id,
        status=run.status.value,
        total_count=run.total_count,
        llm_budget=get_settings().AGENT_LLM_BUDGET_PER_RUN,
        error=run.error,
    )
    try:
        snap = get_thread_state(run_id)
        values = getattr(snap, "values", None) or {}
        out.steps_used = values.get("steps_used")
        out.targets = list(values.get("targets") or [])
        out.insights_created = list(values.get("insights_created") or [])
        if thread_phase(snap) == "interrupted":
            out.pending_approval = snapshot_payload(snap) or None
        out.llm_calls_used = _llm_calls_used(run_id)
    except CheckpointUnavailable:
        pass  # saver chưa dựng được — trả phần tĩnh, client retry sau
    return out


@router.post("/runs/{run_id}/decision")
def submit_decision(
    run_id: uuid.UUID,
    body: AgentDecisionIn,
    db: Session = Depends(get_db),
    user=Depends(require_role("pm", "operations")),
) -> dict:
    """Approve/edit/reject insight đang đợi duyệt — resume graph HITL.

    Response ``{insight_id, review_status, drafts_created}``. reviewer_id lấy
    từ token (KHÔNG tin payload client)."""
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Run không tồn tại.")
    if run.status == RunStatus.completed:
        # covers cả run rỗng-target chưa từng vào graph lẫn thread đã END
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Agent run {run_id} đã hoàn tất — không nhận decision.",
        )

    try:
        final = resume_with_decision(
            run_id, body.model_dump(exclude_none=True), reviewer_id=user.id
        )
    except ReviewAlreadyCompleted as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except LookupError as exc:
        # thread 'start' — run chưa từng khởi động graph dù row tồn tại
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except CheckpointUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from None

    decision = final.get("decision") or {}
    draft = final.get("insight_draft") or {}
    raw_id = decision.get("insight_id") or draft.get("id")
    if not raw_id:
        # crash-dở-dâng heal path chưa tới apply_decision — không có gì để đọc
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Graph chưa sinh insight cho run này.",
        )

    ins = db.get(Insight, uuid.UUID(str(raw_id)))
    drafts_created = int(
        db.scalar(
            select(func.count())
            .select_from(ActionDraft)
            .where(ActionDraft.insight_id == ins.id)
        )
        or 0
    )
    return {
        "insight_id": str(ins.id),
        "review_status": ins.review_status.value,
        "drafts_created": drafts_created,
    }

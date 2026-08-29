"""Routes agent — UNDERSTAND graph + Gate #2 (plan 25; VoC OS §26, §43, §60).

POST /api/agent/runs              : trigger investigation (user question HOẶC
                                    system signal) → 200 {run_id} ngay; graph
                                    chạy background thread tới interrupt.
GET  /api/agent/runs/{id}         : status + interrupt payload (pending_approval)
POST /api/agent/runs/{id}/decision: Gate #2 — approve | edit | investigate_more | reject
GET  /api/insights                : insights (shape mới, evidence mở rộng)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.analysis_run import AnalysisRun
from app.models.evidence import Evidence
from app.models.insight import Insight
from app.models.user import User
from app.schemas.agent import (
    AgentDecisionIn,
    AgentRunCreatedOut,
    AgentRunCreateIn,
    AgentRunStatusOut,
    EvidenceRefOut,
    InsightsListOut,
    InsightOut,
)
from understand_agent import runner as understand_runner

router = APIRouter(
    prefix="/api",
    tags=["agent"],
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("/agent/runs", status_code=status.HTTP_200_OK)
def create_agent_run(
    body: AgentRunCreateIn, db: Session = Depends(get_db)
) -> AgentRunCreatedOut:
    """Trigger investigation — graph chạy nền, dừng ở Gate #2 interrupt."""
    run = understand_runner.start_understand_run(
        db, body.product_id, body.question, body.trigger_type
    )
    return AgentRunCreatedOut(run_id=run.id)


def _load_run(db: Session, run_id: uuid.UUID) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run không tồn tại.")
    return run


@router.get("/agent/runs/{run_id}")
def get_agent_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentRunStatusOut:
    run = _load_run(db, run_id)
    payload = understand_runner.get_run_snapshot(run_id)
    return AgentRunStatusOut(
        run_id=run.id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        error=run.error,
        pipeline_version=run.pipeline_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        pending_approval=payload,
    )


@router.post("/agent/runs/{run_id}/decision")
def decide_agent_run(
    run_id: uuid.UUID,
    body: AgentDecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Gate #2 — reviewer_id LUÔN lấy từ token (không tin client).

    404 run/thread chưa start · 409 thread completed · 503 checkpoint down.
    investigate_more → graph quay lại planner (insight status=investigating).
    """
    run = _load_run(db, run_id)
    try:
        final = understand_runner.resume_with_decision(
            run.id,
            {
                "action": body.action,
                "edited_insight": body.edited_insight,
                "reason": body.reason,
                "reviewer_id": str(user.id),
            },
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except understand_runner.CheckpointUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    except Exception as exc:  # noqa: BLE001 — thread completed/đã quyết → 409
        if "completed" in str(exc).lower() or "đã hoàn tất" in str(exc):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raise
    return {
        "run_id": str(run.id),
        "final_status": final.get("final_status"),
        "insights_created": final.get("insights_created", []),
    }


@router.get("/insights")
def list_insights(
    product_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(
        default=None, pattern="^(pending|approved|edited|rejected|investigating)$"
    ),
    db: Session = Depends(get_db),
) -> InsightsListOut:
    """Insights shape mới; evidence_ids mở rộng thành statements (PII-safe)."""
    conditions = []
    if product_id is not None:
        conditions.append(Insight.product_id == product_id)
    if status_filter is not None:
        conditions.append(Insight.status == status_filter)
    total = db.scalar(select(func.count()).select_from(Insight).where(*conditions))
    rows = db.scalars(
        select(Insight).where(*conditions).order_by(Insight.created_at.desc()).limit(100)
    ).all()

    # Evidence mở rộng: 1 query evidence theo các id được reference
    wanted: set[uuid.UUID] = set()
    for r in rows:
        for e in r.evidence or []:
            try:
                wanted.add(uuid.UUID(str(e)))
            except ValueError:
                continue
    by_id: dict[uuid.UUID, Evidence] = {}
    if wanted:
        for ev in db.scalars(select(Evidence).where(Evidence.id.in_(wanted))).all():
            by_id[ev.id] = ev

    items: list[InsightOut] = []
    for r in rows:
        out = InsightOut.model_validate(r)
        evidence_refs = []
        for e in r.evidence or []:
            try:
                ev = by_id.get(uuid.UUID(str(e)))
            except ValueError:
                continue
            if ev is not None:
                evidence_refs.append(
                    EvidenceRefOut(
                        evidence_id=ev.id,
                        statement=ev.statement,
                        source_tool=ev.source_tool,
                    )
                )
        # InsightOut.evidence là list[Any] — ghi đè bằng refs mở rộng qua dict
        item = out.model_dump()
        item["evidence"] = [e.model_dump(mode="json") for e in evidence_refs]
        items.append(InsightOut.model_validate(item))
    return InsightsListOut(items=items, total=int(total or 0))

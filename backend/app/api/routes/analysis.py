"""Routes analysis — tạo run batch + theo dõi tiến độ (plan 09 §3.2).

Job chạy nền qua FastAPI `BackgroundTasks` (đủ cho ≤1500 rows; KHÔNG
Celery/queue — ngoài scope). POST trả `{run_id}` NGAY sau khi snapshot cấu
hình + đếm total; `run_analysis` tự chạy sau khi response đã gửi.

Snapshot vào row run: `pipeline_version` (hằng code), `llm_model`,
`prompt_version` (= PROMPT_VERSION của classifier), `embedding_model` — để
so sánh kết quả giữa các lần chạy khi config đổi.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.jobs.analysis_runner import PIPELINE_VERSION, run_analysis
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.models.feedback import Feedback
from app.schemas.analysis import (
    AnalysisCostPreviewOut,
    AnalysisRunCreateIn,
    AnalysisScopeIn,
    RunCreatedOut,
    RunListOut,
    RunProgressOut,
)
from app.schemas.feedback import FeedbackListOut, FeedbackOut
from app.services.classifier import PROMPT_VERSION
from app.core.config import get_settings
from app.services.analysis_service import (
    SelectionChangedError,
    preview_analysis,
    select_eligible_feedback,
)

router = APIRouter(
    prefix="/api",
    tags=["analysis"],
    # Guard toàn router: chỉ pm | operations (job tốn tiền LLM tokens).
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("/analysis/runs", status_code=201)
def create_analysis_run(
    body: AnalysisRunCreateIn,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> RunCreatedOut:
    """Claim exactly the import-scoped rows covered by a confirmed receipt."""
    settings = get_settings()
    scope = AnalysisScopeIn.model_validate(body.model_dump())
    try:
        rows, _ = select_eligible_feedback(session, scope, for_update=True)
    except SelectionChangedError:
        raise HTTPException(
            status_code=409,
            detail={"code": "selection_changed", "message": "Selection is no longer eligible."},
        )
    if len(rows) != body.confirmed_item_count:
        raise HTTPException(
            status_code=409,
            detail={"code": "selection_changed", "message": "Pending item count changed; preview again."},
        )
    run = AnalysisRun(
        pipeline_version=PIPELINE_VERSION,
        llm_model=settings.LLM_MODEL,
        prompt_version=PROMPT_VERSION,
        embedding_model=settings.EMBEDDING_MODEL,
        import_id=body.import_id,
        mode=body.mode,
        chunk_size=1 if body.mode == "selected" else settings.ANALYSIS_BATCH_SIZE,
        total_count=len(rows),
    )
    session.add(run)
    session.flush()
    for row in rows:
        row.analysis_run_id = run.id
    session.commit()
    session.refresh(run)

    background_tasks.add_task(run_analysis, run.id)
    return RunCreatedOut(run_id=run.id)


@router.post("/analysis/runs/preview")
def preview_analysis_run(
    body: AnalysisScopeIn,
    session: Session = Depends(get_db),
) -> AnalysisCostPreviewOut:
    try:
        return preview_analysis(session, body)
    except SelectionChangedError:
        raise HTTPException(
            status_code=409,
            detail={"code": "selection_changed", "message": "Some selected feedback is no longer pending."},
        )


@router.get("/analysis/runs")
def list_analysis_runs(
    limit: int = Query(default=30, ge=1, le=100),
    status_filter: list[RunStatus] | None = Query(default=None, alias="status"),
    session: Session = Depends(get_db),
) -> RunListOut:
    conditions = []
    if status_filter:
        conditions.append(AnalysisRun.status.in_(status_filter))
    total = int(
        session.scalar(select(func.count()).select_from(AnalysisRun).where(*conditions)) or 0
    )
    rows = session.scalars(
        select(AnalysisRun)
        .where(*conditions)
        .order_by(AnalysisRun.started_at.desc())
        .limit(limit)
    ).all()
    return RunListOut(
        items=[RunProgressOut.model_validate(row) for row in rows],
        total=total,
    )


@router.post("/analysis/runs/{run_id}/cancel", status_code=202)
def cancel_analysis_run(
    run_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> RunProgressOut:
    run = session.scalar(
        select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run không tồn tại.")
    if run.status != RunStatus.running:
        raise HTTPException(status_code=409, detail="Run không còn chạy.")
    run.cancel_requested_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(run)
    return RunProgressOut.model_validate(run)


@router.get("/analysis/runs/{run_id}")
def get_run_progress(
    run_id: uuid.UUID, session: Session = Depends(get_db)
) -> RunProgressOut:
    """Progress một run: status + processed/total + error summary."""
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run không tồn tại.")
    return RunProgressOut.model_validate(run)


@router.get("/analysis/runs/{run_id}/results")
def get_run_results(
    run_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> FeedbackListOut:
    """Feedback thuộc run (phân trang) kèm kết quả phân loại. Item chưa được
    xử lý xong vẫn nằm trong results với labels NULL — caller tự lọc."""
    if session.get(AnalysisRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Run không tồn tại.")

    conditions = [Feedback.analysis_run_id == run_id]
    total = session.scalar(select(func.count()).select_from(Feedback).where(*conditions))
    rows = session.scalars(
        select(Feedback)
        .where(*conditions)
        .order_by(Feedback.occurred_at, Feedback.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return FeedbackListOut(
        items=[FeedbackOut.model_validate(r) for r in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )

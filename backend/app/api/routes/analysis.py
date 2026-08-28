"""Routes analysis — tạo run batch + theo dõi tiến độ (plan 09 §3.2).

Job chạy nền qua FastAPI `BackgroundTasks` (đủ cho ≤1500 rows; KHÔNG
Celery/queue — ngoài scope). POST trả `{run_id}` NGAY sau khi snapshot cấu
hình + đếm total; `run_analysis` tự chạy sau khi response đã gửi.

Snapshot vào row run: `pipeline_version` (hằng code), `llm_model`,
`prompt_version` (= PROMPT_VERSION của classifier), `embedding_model` — để
so sánh kết quả giữa các lần chạy khi config đổi.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.jobs.analysis_runner import PIPELINE_VERSION, run_analysis
from app.models.analysis_run import AnalysisRun
from app.models.feedback import Feedback
from app.schemas.analysis import RunCreatedOut, RunProgressOut
from app.schemas.feedback import FeedbackListOut, FeedbackOut
from app.services.classifier import PROMPT_VERSION
from app.core.config import get_settings

router = APIRouter(
    prefix="/api",
    tags=["analysis"],
    # Guard toàn router: chỉ pm | operations (job tốn tiền LLM tokens).
    dependencies=[Depends(require_role("pm", "operations"))],
)


@router.post("/analysis/runs", status_code=201)
def create_analysis_run(
    background_tasks: BackgroundTasks, session: Session = Depends(get_db)
) -> RunCreatedOut:
    """Tạo run + đẩy job nền; trả run_id ngay. Idempotent theo nghĩa: chỉ các
    feedback `analysis_run_id IS NULL` được nhặt — chạy nhiều lần không nhân
    đôi công việc (xem `app/jobs/analysis_runner.py`)."""
    settings = get_settings()
    total = session.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.analysis_run_id.is_(None))
    )
    run = AnalysisRun(
        pipeline_version=PIPELINE_VERSION,
        llm_model=settings.LLM_MODEL,
        prompt_version=PROMPT_VERSION,
        embedding_model=settings.EMBEDDING_MODEL,
        total_count=int(total or 0),
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    background_tasks.add_task(run_analysis, run.id)
    return RunCreatedOut(run_id=run.id)


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

"""Routes clusters/reports — reshape VoC OS (plan 21).

Lịch sử: file gốc chứa clusters + insights + reports (Phase 14–16). Reshape
2026-08-28: endpoints insights (services/insight.py) và KPI 3-latency chết
cùng bảng cũ — insights mới đến ở plan 25 (UNDERSTAND), KPIs ở plan 27.
Giữ lại: POST /clusters/run + GET /clusters (C1/C5) + GET /reports/summary (C4).

Guard role pm|operations gắn ở TẦNG ROUTER như feedback router.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.cluster import Cluster
from app.schemas.cluster import ClusterOut, ClusterRunOut, ClustersListOut
from app.schemas.report import (
    ReportKpisOut,
    ReportSummaryOut,
    SummaryWindow,
)
from app.services.clustering import run_clustering, sample_feedback_ids_by_cluster
from app.services.reports import build_kpis, build_summary

router = APIRouter(
    prefix="/api",
    tags=["clusters"],
    # Guard toàn router: chỉ pm | operations.
    dependencies=[Depends(require_role("pm", "operations"))],
)

_SORT_COLUMNS = {
    "feedback_count": Cluster.feedback_count.desc(),
    "growth_ratio": Cluster.growth_ratio.desc(),
    "recent": Cluster.last_seen.desc(),  # `recent` = last_seen giảm dần (C1)
}


@router.post("/clusters/run", status_code=status.HTTP_200_OK)
def run_clusters(db: Session = Depends(get_db)) -> ClusterRunOut:
    """Chạy lại toàn bộ clustering — idempotent trong 1 transaction (C5).

    Sync def: threadpool của FastAPI đủ cho dataset ≤1500 row; LLM naming +
    HDBSCAN chạy trong thread này không block event loop.
    """
    t0 = time.perf_counter()
    try:
        stats = run_clustering(db)
    except Exception:  # noqa: BLE001 — 500 chuẩn không leak chi tiết nội bộ
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clustering run thất bại — DB đã rollback về trạng thái cũ.",
        )
    return ClusterRunOut(
        clusters_upserted=stats.clusters_upserted,
        assigned_count=stats.assigned_count,
        unassigned_count=stats.unassigned_count,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )


@router.get("/clusters")
def list_clusters(
    sort: str = Query(
        default="feedback_count",
        pattern="^(feedback_count|growth_ratio|recent)$",
    ),
    db: Session = Depends(get_db),
) -> ClustersListOut:
    """Danh sách cụm theo C1; chưa từng chạy clustering → items rỗng (200)."""
    clusters = (
        db.execute(select(Cluster).order_by(_SORT_COLUMNS[sort])).scalars().all()
    )
    if not clusters:
        return ClustersListOut(items=[])

    # sample_feedback_ids: helper dùng chung với emerging của reports (C4)
    samples = sample_feedback_ids_by_cluster(db)

    return ClustersListOut(
        items=[
            ClusterOut.model_validate(c).model_copy(
                update={"sample_feedback_ids": samples.get(c.id, [])}
            )
            for c in clusters
        ]
    )


@router.get("/reports/summary")
def reports_summary(
    days: SummaryWindow = SummaryWindow.W30,
    db: Session = Depends(get_db),
) -> ReportSummaryOut:
    """Báo cáo tổng hợp PM thuần SQL (C4) trên cửa sổ event-time `days` ngày.

    Giá trị `days` khác 7/30/90 → FastAPI tự 422; thiếu dữ liệu vẫn 200
    (key 0 / mảng rỗng) — không bao giờ lỗi vì "chưa có cụm".
    """
    return ReportSummaryOut.model_validate(
        build_summary(db, days=int(days), now=datetime.now(timezone.utc))
    )


@router.get("/reports/kpis")
def reports_kpis(db: Session = Depends(get_db)) -> ReportKpisOut:
    """KPI 3-latency + evaluation 3 HITL gate (VoC OS §65–67) — thuần SQL.

    Bảng trống / chưa đo → median null, count 0 (200)."""
    return ReportKpisOut.model_validate(
        build_kpis(db, now=datetime.now(timezone.utc))
    )

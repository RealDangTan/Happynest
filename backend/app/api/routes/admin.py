"""Routes clusters/insights/reports — Phase 14–16 đã thay hết stub 501.

Lịch sử file: gốc là stub 501 cho 3 nhóm endpoint giai đoạn sau (Phase 05).
Phase 13 đã thay reviews/corrections bằng routes/review.py riêng. Phase 14
thay stub /clusters bằng route thật (engine services/clustering.py); Phase 15
thay stub /insights bằng engine services/insight.py; Phase 16 thay stub
/reports/summary bằng aggregate thuần SQL (services/reports.py).

Guard role pm|operations gắn ở TẦNG ROUTER như feedback router.
"""

import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.cluster import Cluster
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.schemas.cluster import ClusterOut, ClusterRunOut, ClustersListOut
from app.schemas.insight import EvidenceOut, InsightsListOut, InsightsRunOut, InsightOut
from app.schemas.report import ReportKpisOut, ReportSummaryOut, SummaryWindow
from app.services.clustering import run_clustering, sample_feedback_ids_by_cluster
from app.services.insight import run_insights as run_insights_service
from app.services.reports import build_kpis, build_summary

router = APIRouter(
    prefix="/api",
    tags=["clusters"],
    # Guard toàn router (kể cả stub còn lại): chỉ pm | operations.
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


@router.post("/insights/run", status_code=status.HTTP_200_OK)
def run_insights_endpoint(db: Session = Depends(get_db)) -> InsightsRunOut:
    """Sinh insight cho các cụm ưu tiên cao — replace-all idempotent (C6).

    409 khi chưa có cụm nào (SELECT 1 LIMIT 1, không phải exception) kèm hướng
    dẫn bước tiếp theo. Field `skipped` ngoài hợp đồng C6 — được phép vì C6
    không cấm field bổ sung (plan Step 3.1). Sync def như run_clusters.
    """
    has_cluster = db.execute(select(Cluster.id).limit(1)).first() is not None
    if not has_cluster:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chưa có cụm nào. Chạy POST /api/clusters/run trước.",
        )
    stats = run_insights_service(db)
    return InsightsRunOut(
        insights_generated=stats.insights_generated,
        duration_ms=stats.duration_ms,
        skipped=stats.skipped,
    )


@router.get("/insights")
def list_insights(db: Session = Depends(get_db)) -> InsightsListOut:
    """Danh sách insight theo C2 — evidence_ids JSONB mở rộng thành object
    {feedback_id, snippet≤200-từ-sanitized, severity, created_at}.

    Chưa từng chạy /insights/run → items rỗng (200). Dẫn chứng trỏ feedback
    đã bị xoá → bị bỏ khỏi mảng; >5 trong JSONB (không thể xảy ra do Task 2)
    vẫn cắt còn 5 phòng thủ (Step 3.2).
    """
    rows = db.execute(select(Insight)).scalars().all()
    if not rows:
        return InsightsListOut(items=[])

    id_lists: list[list[UUID]] = [
        [UUID(s) for s in (r.evidence_ids or [])[:5]] for r in rows
    ]
    flat = [fid for ids in id_lists for fid in ids]
    by_id: dict[UUID, Feedback] = {}
    if flat:
        fb_rows = db.execute(select(Feedback).where(Feedback.id.in_(flat))).scalars()
        by_id = {fb.id: fb for fb in fb_rows}

    items: list[InsightOut] = []
    for row, ids in zip(rows, id_lists):
        evidence = []
        for fid in ids:
            fb = by_id.get(fid)
            if fb is None:
                continue
            evidence.append(
                EvidenceOut(
                    feedback_id=fb.id,
                    snippet=(fb.sanitized_content or "")[:200],
                    severity=getattr(fb.severity, "value", fb.severity),
                    created_at=fb.created_at,
                )
            )
        items.append(
            InsightOut(
                id=row.id,
                cluster_id=row.cluster_id,
                title=row.title,
                summary=row.summary,
                suggested_action=row.suggested_action,
                review_status=getattr(row.review_status, "value", row.review_status),
                evidence=evidence,
            )
        )
    return InsightsListOut(items=items)


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
    """KPI 3-latency + closed-loop thuần SQL (phase 20) — KHÔNG đụng C4.

    Bảng trống / chưa đo → median null, count 0 (200); sai role → 403
    (guard router-level như summary)."""
    return ReportKpisOut.model_validate(
        build_kpis(db, now=datetime.now(timezone.utc))
    )

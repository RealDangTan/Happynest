"""Routes clusters + các stub còn lại — Phase 14 thay stub `/api/clusters`.

Lịch sử file: gốc là stub 501 cho 3 nhóm endpoint giai đoạn sau (Phase 05).
Phase 13 đã thay reviews/corrections bằng routes/review.py riêng. Phase 14
này thay stub /clusters bằng route thật (engine services/clustering.py);
/insights và /reports/summary còn stub chờ plans 15–16.

Guard role pm|operations gắn ở TẦNG ROUTER như feedback router.
"""

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.cluster import Cluster
from app.models.feedback import Feedback
from app.schemas.cluster import ClusterOut, ClusterRunOut, ClustersListOut
from app.services.clustering import run_clustering

router = APIRouter(
    prefix="/api",
    tags=["clusters"],
    # Guard toàn router (kể cả stub còn lại): chỉ pm | operations.
    dependencies=[Depends(require_role("pm", "operations"))],
)

_SAMPLE_LIMIT = 5

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

    # sample_feedback_ids: ≤5 member MỚI NHẤT mỗi cụm — 1 query duy nhất,
    # group python-side (dataset ≤1500 nên rẻ hơn window function).
    pairs = db.execute(
        select(Feedback.cluster_id, Feedback.id)
        .where(Feedback.cluster_id.is_not(None))
        .order_by(Feedback.created_at.desc())
    ).all()
    samples: dict[UUID, list[UUID]] = {}
    for cluster_id, feedback_id in pairs:
        bucket = samples.setdefault(cluster_id, [])
        if len(bucket) < _SAMPLE_LIMIT:
            bucket.append(feedback_id)

    return ClustersListOut(
        items=[
            ClusterOut.model_validate(c).model_copy(
                update={"sample_feedback_ids": samples.get(c.id, [])}
            )
            for c in clusters
        ]
    )


@router.get("/insights")
def list_insights():
    """STUB 501 — insight generation evidence-backed thuộc phase 15 (plan 15).
    Bảng `insights` đã có sẵn."""
    raise HTTPException(
        status_code=501,
        detail="GET /api/insights chưa triển khai. Cần insight engine (plan 15).",
    )


@router.get("/reports/summary")
def reports_summary():
    """STUB 501 — báo cáo tổng hợp cho PM là phase 16 (plan 16, thuần SQL)."""
    raise HTTPException(
        status_code=501,
        detail="GET /api/reports/summary chưa triển khai. Cần reports layer (plan 16).",
    )

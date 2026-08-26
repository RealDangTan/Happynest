"""Tool `get_cluster_metrics` — số liệu + trend 1 cụm (phase 18 Task 3).

Trend fields (current/previous/growth_ratio/is_emerging/is_spike/suggested_priority,
first_seen/last_seen) đọc THẲNG các cột phase 14 đã lưu trên row `clusters` —
tool KHÔNG tính lại trend (công thức canonical nằm ở services/clustering.py).
Chỉ member_count / severity_dist / top_categories query live từ feedbacks.
Cluster id lạ → ValueError("cluster not found") — graph biến thành observation
lỗi, không crash.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from happynest_agent.tools.base import ToolInput, ToolSpec
from app.models.cluster import Cluster
from app.models.feedback import Feedback


class MetricsIn(ToolInput):
    cluster_id: uuid.UUID


class CategoryCount(BaseModel):
    category: str
    count: int


class ClusterMetricsOut(BaseModel):
    cluster_id: uuid.UUID
    name: str
    summary: str
    member_count: int
    first_seen: object  # datetime — giữ raw để router tự format
    last_seen: object
    current_count: int
    previous_count: int
    growth_ratio: float
    is_emerging: bool
    is_spike: bool
    suggested_priority: float | None
    severity_dist: dict[str, int]
    top_categories: list[CategoryCount]  # ≤5, giảm dần theo count


def execute(db: Session, params: MetricsIn) -> ClusterMetricsOut:
    cluster = db.get(Cluster, params.cluster_id)
    if cluster is None:
        raise ValueError("cluster not found")

    member_count = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.cluster_id == params.cluster_id)
    )

    severity_rows = db.execute(
        select(Feedback.severity, func.count())
        .where(Feedback.cluster_id == params.cluster_id)
        .group_by(Feedback.severity)
    ).all()
    severity_dist = {
        (s.value if hasattr(s, "value") else str(s)): n for s, n in severity_rows
    }

    # Explode JSONB array categories — chỉ row có categories; top 5 giảm dần.
    cat_rows = db.execute(
        text(
            "SELECT cat AS category, count(*) AS n "
            "FROM feedbacks, jsonb_array_elements_text(categories) AS cat "
            "WHERE cluster_id = :cid "
            "GROUP BY cat ORDER BY n DESC, cat ASC LIMIT :lim"
        ),
        {"cid": params.cluster_id, "lim": 5},
    ).all()

    return ClusterMetricsOut(
        cluster_id=cluster.id,
        name=cluster.name,
        summary=cluster.summary,
        member_count=member_count or 0,
        first_seen=cluster.first_seen,
        last_seen=cluster.last_seen,
        current_count=cluster.current_count,
        previous_count=cluster.previous_count,
        growth_ratio=cluster.growth_ratio,
        is_emerging=cluster.is_emerging,
        is_spike=cluster.is_spike,
        suggested_priority=cluster.suggested_priority,
        severity_dist=severity_dist,
        top_categories=[
            CategoryCount(category=c, count=n) for c, n in cat_rows
        ],
    )


SPEC = ToolSpec(
    name="get_cluster_metrics",
    description=(
        "Return stored trend fields plus live member, severity and category "
        "breakdown for one cluster."
    ),
    input_model=MetricsIn,
    output_model=ClusterMetricsOut,
)

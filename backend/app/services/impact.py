"""Closed-loop impact check (phase 20 Task 1) — "hành động đã có tác dụng?".

Với mỗi insight ĐÃ duyệt (approved/edited) CÓ draft_ticket, đủ tuổi
``IMPACT_WINDOW_DAYS`` và CHƯA được đo: lấy mốc hành động ``t`` = MIN(
action_drafts.created_at), đếm volume feedback của cụm trong cửa sổ W ngày
TRƯỚC và SAU ``t``, ghi 1 row `impact_checks` với delta_ratio.

Thuần SQL — KHÔNG một call LLM (phi KPI phase 20). Idempotent theo insight_id:
rerun bỏ qua insight đã có row đo (không nhân bản).

Trigger TAY qua caller (route/script) — non-goal scheduler tự chạy.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.action_draft import ActionDraft
from app.models.cluster import Cluster
from app.models.enums import DraftKind, ReviewStatus
from app.models.feedback import Feedback
from app.models.impact_check import ImpactCheck
from app.models.insight import Insight

logger = logging.getLogger(__name__)


def run_impact_checks(db: Session, settings: Settings | None = None) -> dict[str, Any]:
    """Đo impact mọi insight đủ điều kiện; trả {checks_inserted, items:[…]}."""
    s = settings or get_settings()
    window = timedelta(days=s.IMPACT_WINDOW_DAYS)
    now = datetime.now(timezone.utc)
    cutoff = now - window

    # insights đã finalized-thành-công + có ticket draft + đủ tuổi + chưa đo
    has_ticket = exists().where(
        ActionDraft.insight_id == Insight.id,
        ActionDraft.kind == DraftKind.draft_ticket,
    )
    already_measured = exists().where(ImpactCheck.insight_id == Insight.id)
    candidates = db.scalars(
        select(Insight)
        .where(
            Insight.review_status.in_([ReviewStatus.approved, ReviewStatus.edited]),
            has_ticket,
            Insight.created_at <= cutoff,
            ~already_measured,
        )
        .order_by(Insight.created_at)
    ).all()

    items: list[dict[str, Any]] = []
    for ins in candidates:
        t = db.scalar(
            select(func.min(ActionDraft.created_at)).where(
                ActionDraft.insight_id == ins.id
            )
        )
        if t is None:  # phòng thủ — EXISTS đã lọc nhưng an toàn hơn
            continue

        def _count(lo: datetime, hi: datetime) -> int:
            return int(
                db.scalar(
                    select(func.count())
                    .select_from(Feedback)
                    .where(
                        Feedback.cluster_id == ins.cluster_id,
                        Feedback.created_at >= lo,
                        Feedback.created_at < hi,
                    )
                )
                or 0
            )

        before = _count(t - window, t)
        after = _count(t, t + window)
        delta = round((after - before) / max(before, 1), 3)

        cluster_name = (
            db.scalar(select(Cluster.name).where(Cluster.id == ins.cluster_id))
            if ins.cluster_id is not None
            else None
        )
        db.add(
            ImpactCheck(
                insight_id=ins.id,
                cluster_id=ins.cluster_id,
                cluster_name=cluster_name or "(cụm đã xoá)",
                checked_at=t + window,
                window_days=s.IMPACT_WINDOW_DAYS,
                before_count=before,
                after_count=after,
                delta_ratio=delta,
            )
        )
        items.append(
            {
                "insight_id": str(ins.id),
                "cluster_name": cluster_name or "(cụm đã xoá)",
                "before": before,
                "after": after,
                "delta_ratio": delta,
            }
        )

    db.commit()
    logger.info("impact check: %d insight mới được đo", len(items))
    return {"checks_inserted": len(items), "items": items}

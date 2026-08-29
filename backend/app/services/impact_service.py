"""Impact check — closed loop (VoC OS tái dựng, plan 27 Task 2).

Đo volume feedback (match `affected_context` của insight trong `data` JSONB)
trước/sau mốc action được tạo, window `IMPACT_WINDOW_DAYS`. Idempotent per
action. Trigger: CLI `scripts/run_impact_checks.py` (điền gap "no trigger"
của phase 20).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.action import Action
from app.models.decision_log import DecisionLog
from app.models.enums import DecisionSubject
from app.models.insight import Insight

_CHECK_SQL = text("""
    SELECT count(*) FROM feedback f
    WHERE f.product_id = :pid
      AND f.occurred_at >= :start AND f.occurred_at < :end
""")

_CHECK_MATCH_SQL = text("""
    SELECT count(*) FROM feedback f
    WHERE f.product_id = :pid
      AND f.occurred_at >= :start AND f.occurred_at < :end
      AND f.data @> CAST(:match AS jsonb)
""")


def _match_filter(insight: Insight) -> str | None:
    """affected_context → JSONB containment (chỉ field có trong `data`)."""
    ctx = insight.affected_context or {}
    if not ctx:
        return None
    import json

    return json.dumps(ctx, ensure_ascii=False)


def run_impact_checks(db: Session, now: datetime | None = None) -> list[dict]:
    """Đo closed-loop cho action accepted/edited aged đủ window; idempotent."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    window = timedelta(days=settings.IMPACT_WINDOW_DAYS)
    results: list[dict] = []

    actions = db.scalars(
        select(Action).where(Action.status.in_(["accepted", "edited"]))
    ).all()
    for action in actions:
        # idempotent: đã đo cho action này → bỏ qua
        from app.models.impact_check import ImpactCheck

        existing = db.scalars(
            select(ImpactCheck.id).where(ImpactCheck.action_id == action.id)
        ).first()
        if existing is not None:
            continue

        action_time = action.created_at
        if action_time.tzinfo is None:
            action_time = action_time.replace(tzinfo=timezone.utc)
        if now - action_time < window:
            continue  # chưa đủ tuổi đo

        insight = db.get(Insight, action.insight_id)
        if insight is None:
            continue
        match = _match_filter(insight)
        stmt = _CHECK_MATCH_SQL if match else _CHECK_SQL
        params_base = {"pid": str(insight.product_id)}
        if match:
            params_base["match"] = match
        before = int(
            db.execute(
                stmt,
                {**params_base, "start": action_time - window, "end": action_time},
            ).scalar()
            or 0
        )
        after = int(
            db.execute(
                stmt,
                {**params_base, "start": action_time, "end": action_time + window},
            ).scalar()
            or 0
        )
        delta_ratio = round((after - before) / before, 4) if before else None

        check = ImpactCheck(
            action_id=action.id,
            insight_id=insight.id,
            checked_at=now,
            window_days=settings.IMPACT_WINDOW_DAYS,
            before_count=before,
            after_count=after,
            delta_ratio=delta_ratio,
        )
        db.add(check)
        db.commit()
        results.append(
            {
                "action_id": str(action.id),
                "insight_id": str(insight.id),
                "before_count": before,
                "after_count": after,
                "delta_ratio": delta_ratio,
            }
        )
    return results

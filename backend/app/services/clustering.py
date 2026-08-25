"""Clustering engine — Phase 14 (plan 14 §3 Task 2/3).

Trend formulas là CÔNG THỨC CHUẨN chốt cứng trong plan (executor copy nguyên
xi, không tự chế); đổi scale `suggested_priority` sau này phải qua decisions.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.core.config import Settings


def compute_trend(
    members: Sequence, now: datetime, settings: Settings
) -> dict:
    """Tính trend fields cho 1 cụm từ members (duck-typed: created_at, severity).

    Trả dict khớp các cột trend của bảng `clusters`:
    feedback_count, first_seen, last_seen, current_count, previous_count,
    growth_ratio, is_emerging, is_spike, suggested_priority.
    """
    window = timedelta(days=settings.CLUSTER_WINDOW_DAYS)
    current_cut = now - window          # [now−W, now]
    previous_cut = now - 2 * window     # [now−2W, now−W)

    in_current = [m for m in members if current_cut <= m.created_at <= now]
    in_previous = [
        m for m in members if previous_cut <= m.created_at < current_cut
    ]
    current = len(in_current)
    previous = len(in_previous)

    # growth_ratio: chặn inf ra JSON — previous==0 → trần 9.99 khi có current
    if previous > 0:
        growth_ratio = round(current / previous, 2)
    else:
        growth_ratio = 9.99 if current > 0 else 0.0

    is_spike = (
        previous > 0
        and current >= settings.CLUSTER_SPIKE_MIN_CURRENT
        and current / previous >= settings.CLUSTER_SPIKE_RATIO
    )
    is_emerging = previous == 0 and current >= settings.CLUSTER_EMERGING_MIN

    created = sorted(m.created_at for m in members)
    high_critical = sum(
        1 for m in members if getattr(m, "severity", None) in ("high", "critical")
    )
    suggested_priority = round(
        0.5 * min(len(members) / 50, 1)
        + 0.3 * (1 if (is_spike or is_emerging) else 0)
        + 0.2 * (high_critical / len(members)),
        2,
    )

    return {
        "feedback_count": len(members),
        "first_seen": created[0],
        "last_seen": created[-1],
        "current_count": current,
        "previous_count": previous,
        "growth_ratio": growth_ratio,
        "is_emerging": is_emerging,
        "is_spike": is_spike,
        "suggested_priority": suggested_priority,
    }

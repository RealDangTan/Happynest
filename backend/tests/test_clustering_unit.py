"""Unit test thuần hàm compute_trend — Phase 14 Task 2.

Không chạm DB, không mock LLM: members là SimpleNamespace(created_at, severity).
Công thức chuẩn copy nguyên xi từ plan 14 §3 Task 2 — fixture phủ cả 4 nhánh:
spike / emerging / ratio bình thường / cụm cũ xa.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.clustering import compute_trend

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

SETTINGS_STUB = SimpleNamespace(
    CLUSTER_WINDOW_DAYS=30,
    CLUSTER_SPIKE_RATIO=2.0,
    CLUSTER_SPIKE_MIN_CURRENT=5,
    CLUSTER_EMERGING_MIN=3,
)


def _member(days_ago: float, severity: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        created_at=NOW - timedelta(days=days_ago), severity=severity
    )


def test_branch_spike() -> None:
    """current≥min_current và gấp đôi previous → spike, ratio 2.0."""
    members = (
        [_member(45) for _ in range(4)]      # previous window [−60d, −30d)
        + [_member(5) for _ in range(8)]     # current window [−30d, now]
        + [_member(5, "high") for _ in range(3)]
    )
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["feedback_count"] == 15
    assert t["current_count"] == 11
    assert t["previous_count"] == 4
    assert t["growth_ratio"] == 2.75
    assert t["is_spike"] is True
    assert t["is_emerging"] is False
    # 0.5·min(15/50,1)=0.15 · +0.3 spike · +0.2·(3/15)=0.04 → 0.49
    assert t["suggested_priority"] == 0.49
    assert t["first_seen"] == min(m.created_at for m in members)
    assert t["last_seen"] == max(m.created_at for m in members)


def test_branch_emerging() -> None:
    """previous==0, current≥EMERGING_MIN → cụm hoàn toàn mới, ratio trần 9.99."""
    members = [_member(10) for _ in range(5)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["current_count"] == 5
    assert t["previous_count"] == 0
    assert t["growth_ratio"] == 9.99
    assert t["is_spike"] is False
    assert t["is_emerging"] is True


def test_branch_normal_ratio_below_thresholds() -> None:
    """Có cả hai cửa sổ nhưng chưa chạm ngưỡng spike → chỉ ratio thường."""
    members = [_member(40) for _ in range(6)] + [_member(10) for _ in range(4)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["current_count"] == 4
    assert t["previous_count"] == 6
    assert t["growth_ratio"] == 0.67  # round(4/6, 2)
    assert t["is_spike"] is False     # current 4 < SPIKE_MIN_CURRENT
    assert t["is_emerging"] is False


def test_branch_stale_cluster() -> None:
    """Toàn bộ member ngoài 2 cửa sổ → current=previous=0, ratio 0.0."""
    members = [_member(100) for _ in range(7)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["feedback_count"] == 7
    assert t["current_count"] == 0
    assert t["previous_count"] == 0
    assert t["growth_ratio"] == 0.0
    assert t["is_spike"] is False
    assert t["is_emerging"] is False

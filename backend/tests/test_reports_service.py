"""Test service reports.build_summary — Phase 16 Task 1 (plan 16).

DB-backed theo chiến lược conftest Phase 11: mọi INSERT đi qua fixture
`db_session` và ROLLBACK khi test xong — không để lại row `rep-it-` nào trên
DB dev dùng chung (đáp ứng ý đồ "dọn rác theo prefix" của plan mà không cần
DELETE tay). Không LLM, không mock — thuần SQL như hợp đồng C4.

Chạy:  uv run pytest tests/test_reports_service.py -q   (SKIP khi DB offline)
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.reports import SENTIMENT_KEYS, SEVERITY_KEYS, build_summary
from tests.conftest import _SKIP_MSG, db_reachable


@pytest.fixture(autouse=True)
def _needs_real_db():
    """Service chạm Supabase thật như các suite hiện hành — SKIP khi offline."""
    if not db_reachable():
        pytest.skip(_SKIP_MSG)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def _fb(external_ref: str, **kwargs) -> dict:
    """Row seed tối giản trong cửa sổ; external_ref prefix rep-it- để nhận diện."""
    base = {
        "external_ref": f"rep-it-{external_ref}",
        "source": "unit-test",
        "created_at": NOW - timedelta(days=1),
        "raw_content": "raw unit test (không bao giờ ra khỏi biên sanitize)",
        "sanitized_content": "sanitized unit test",
    }
    base.update(kwargs)
    return base


def test_totals_filters_and_window(db_session) -> None:
    from app.models.feedback import Feedback

    # DB dev DÙNG CHUNG có sẵn row demo → mọi assertion so DELTA với baseline
    base = build_summary(db_session, days=7, now=NOW)["totals"]

    db_session.add_all(
        [
            Feedback(**_fb("t1")),                                    # thường
            Feedback(**_fb("t2", review_status="pending")),
            Feedback(**_fb("t3", pii_detected=True)),
            Feedback(
                **_fb(
                    "t4",
                    review_status="pending",
                    pii_detected=True,
                )
            ),
            # ngoài cửa sổ days=7 → không được đếm dù pending + pii
            Feedback(
                **_fb(
                    "t5",
                    created_at=NOW - timedelta(days=20),
                    review_status="pending",
                    pii_detected=True,
                )
            ),
        ]
    )
    db_session.flush()

    out = build_summary(db_session, days=7, now=NOW)
    assert out["window_days"] == 7
    assert out["totals"]["feedback_count"] == base["feedback_count"] + 4
    assert out["totals"]["pending_review_count"] == base["pending_review_count"] + 2
    assert out["totals"]["pii_detected_count"] == base["pii_detected_count"] + 2


def test_by_enums_null_excluded_and_zero_keys_kept(db_session) -> None:
    from app.models.feedback import Feedback

    base_out = build_summary(db_session, days=30, now=NOW)

    db_session.add_all(
        [
            Feedback(**_fb("s1", severity="low", sentiment="negative")),
            Feedback(**_fb("s2", severity="critical", sentiment="mixed")),
            Feedback(**_fb("s3", sentiment="positive")),      # severity NULL → loại
            Feedback(**_fb("s4", severity="high")),           # sentiment NULL → loại
        ]
    )
    db_session.flush()
    out = build_summary(db_session, days=30, now=NOW)

    assert list(out["by_severity"]) == SEVERITY_KEYS
    assert out["by_severity"]["low"] == base_out["by_severity"]["low"] + 1
    assert out["by_severity"]["critical"] == base_out["by_severity"]["critical"] + 1
    assert out["by_severity"]["high"] == base_out["by_severity"]["high"] + 1
    assert out["by_severity"]["medium"] == base_out["by_severity"]["medium"]
    # key `mixed` tồn tại (lệch C4 có chủ đích — decisions 2026-08-26)
    assert list(out["by_sentiment"]) == SENTIMENT_KEYS
    assert out["by_sentiment"]["negative"] == base_out["by_sentiment"]["negative"] + 1
    assert out["by_sentiment"]["mixed"] == base_out["by_sentiment"]["mixed"] + 1
    assert out["by_sentiment"]["positive"] == base_out["by_sentiment"]["positive"] + 1
    assert out["by_sentiment"]["neutral"] == base_out["by_sentiment"]["neutral"]


def test_top_categories_merges_duplicates_and_orders(db_session) -> None:
    from app.models.feedback import Feedback

    base_cats = {
        item["category"]: item["count"]
        for item in build_summary(db_session, days=30, now=NOW)["top_categories"]
    }

    db_session.add_all(
        [
            # topic-a x3, topic-b x2 — đủ nặng để KHÔNG bị LIMIT 10 cắt
            # (DB dev chung có sẵn nhiều category đếm-1 cạnh tranh)
            Feedback(**_fb("c1", categories=["rep-it-topic-a", "rep-it-topic-a", "rep-it-topic-b"])),
            Feedback(**_fb("c2", categories=["rep-it-topic-a", "rep-it-topic-b"])),
            Feedback(**_fb("c3", categories=None)),               # json-null không nổ query
            Feedback(
                **_fb(
                    "c4",
                    categories=["rep-it-old-topic"],
                    created_at=NOW - timedelta(days=60),          # ngoài cửa sổ
                )
            ),
        ]
    )
    db_session.flush()
    out = build_summary(db_session, days=30, now=NOW)

    cats = {item["category"]: item["count"] for item in out["top_categories"]}
    assert cats["rep-it-topic-a"] == base_cats.get("rep-it-topic-a", 0) + 3  # trùng gộp đúng
    assert cats["rep-it-topic-b"] == base_cats.get("rep-it-topic-b", 0) + 2
    assert "rep-it-old-topic" not in cats   # prefix unique + ngoài cửa sổ → bị loại hẳn


def test_emerging_shape_sub_c1_with_samples(db_session) -> None:
    import uuid

    from app.models.cluster import Cluster
    from app.models.feedback import Feedback

    cluster = Cluster(
        id=uuid.uuid4(),
        name="Cụm test",
        summary="tổng hợp test",
        feedback_count=2,
        first_seen=NOW - timedelta(days=2),
        last_seen=NOW - timedelta(days=1),
        current_count=2,
        previous_count=0,
        growth_ratio=9.99,
        is_emerging=True,
        is_spike=False,
        suggested_priority=0.8,
    )
    db_session.add(cluster)
    members = [
        Feedback(**_fb(f"e{i}", cluster_id=cluster.id)) for i in range(7)
    ]
    quiet = Cluster(  # cụm thường — KHÔNG emerging/spike → không vào mảng
        id=uuid.uuid4(),
        name="Cụm thường",
        summary="-",
        feedback_count=1,
        first_seen=NOW - timedelta(days=1),
        last_seen=NOW - timedelta(days=1),
        current_count=1,
        previous_count=1,
        growth_ratio=1.0,
        is_emerging=False,
        is_spike=False,
        suggested_priority=0.99,   # priority cao hơn nhưng không đủ điều kiện
    )
    db_session.add(quiet)
    db_session.add_all(members)
    db_session.flush()

    out = build_summary(db_session, days=30, now=NOW)
    assert len(out["emerging"]) == 1
    item = out["emerging"][0]
    assert set(item) == {
        "id", "name", "summary", "feedback_count", "first_seen", "last_seen",
        "current_count", "previous_count", "growth_ratio", "is_emerging",
        "is_spike", "suggested_priority", "sample_feedback_ids",
    }
    assert len(item["sample_feedback_ids"]) <= 5       # ≤5 dù có 7 member
    assert item["is_emerging"] is True and item["is_spike"] is False

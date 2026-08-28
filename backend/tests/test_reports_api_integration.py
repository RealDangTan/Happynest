"""Integration test reports summary API trên data demo thật — plan 16 §3 Task 2.

Chạy: `uv run pytest -m integration tests/test_reports_api_integration.py -v`
Cần Supabase reachable (autouse fixture sẽ SKIP khi offline). KHÔNG seed thêm
row, KHÔNG LLM — endpoint thuần SQL nên test cũng chỉ đối chiếu số liệu.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.enums import UserRole
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

_C4_FIELDS = {
    "generated_at", "window_days", "totals", "by_severity",
    "by_sentiment", "top_categories", "emerging",
}
_C4_TOTALS = {"feedback_count", "pii_detected_count"}
_EMERGING_SUB_C1 = {
    "id", "name", "summary", "feedback_count", "first_seen", "last_seen",
    "current_count", "previous_count", "growth_ratio", "is_emerging",
    "is_spike", "suggested_priority", "sample_feedback_ids",
}


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_summary_shape_c4_and_consistency(client: TestClient) -> None:
    auth = _login(client)
    resp = client.get("/api/reports/summary", headers=auth)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert set(body) == _C4_FIELDS, set(body) ^ _C4_FIELDS
    assert body["window_days"] == 30                      # default
    assert set(body["totals"]) == _C4_TOTALS
    # key enum luôn đủ dù thiếu dữ liệu (thứ tự contracts; mixed theo decisions)
    assert list(body["by_severity"]) == ["low", "medium", "high", "critical"]
    assert list(body["by_sentiment"]) == ["positive", "neutral", "negative", "mixed"]
    # tổng by_* ≤ feedback_count (≤ vì row chưa classify có NULL bị loại)
    assert sum(body["by_severity"].values()) <= body["totals"]["feedback_count"]
    assert sum(body["by_sentiment"].values()) <= body["totals"]["feedback_count"]

    # top_categories: ≤10, shape + sort count giảm dần
    cats = body["top_categories"]
    assert len(cats) <= 10
    for item in cats:
        assert set(item) == {"category", "count"}
    counts = [c["count"] for c in cats]
    assert counts == sorted(counts, reverse=True)

    # emerging: ≤5, mỗi item là shape con C1, samples ≤5
    emerging = body["emerging"]
    assert len(emerging) <= 5
    for item in emerging:
        assert set(item) == _EMERGING_SUB_C1, set(item) ^ _EMERGING_SUB_C1
        assert len(item["sample_feedback_ids"]) <= 5


def test_summary_window_changes_results(client: TestClient, test_product) -> None:
    """days=7 vs days=90 phải khác nhau — suite tự seed 2 row spread ngày
    (reshape 2026-08-28: data demo cũ đã bị migration 0008 wipe)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import or_

    from app.db.session import SessionLocal
    from app.models.feedback import Feedback

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add_all(
            [
                Feedback(
                    product_id=test_product.id,
                    source="test-reports-api",
                    source_record_id="reportsapi-recent",
                    occurred_at=now,                      # trong days=7
                    raw_content="recent row (khong PII)",
                    feedback_text="recent row",
                ),
                Feedback(
                    product_id=test_product.id,
                    source="test-reports-api",
                    source_record_id="reportsapi-old",
                    occurred_at=now - timedelta(days=20),  # ngoài 7, trong 90
                    raw_content="old row (khong PII)",
                    feedback_text="old row",
                ),
            ]
        )
        db.commit()

    try:
        auth = _login(client)
        r7 = client.get("/api/reports/summary", params={"days": 7}, headers=auth)
        r90 = client.get("/api/reports/summary", params={"days": 90}, headers=auth)
        assert r7.status_code == r90.status_code == 200, f"{r7.text} / {r90.text}"

        b7, b90 = r7.json(), r90.json()
        assert b7["window_days"] == 7 and b90["window_days"] == 90
        # cửa sổ hẹp hơn → tổng không bao giờ lớn hơn
        assert b7["totals"]["feedback_count"] <= b90["totals"]["feedback_count"]
        # row cũ (20 ngày) nằm trong 90 nhưng ngoài 7 → khác nhau thật sự
        assert b7["totals"]["feedback_count"] < b90["totals"]["feedback_count"]
    finally:
        with SessionLocal() as db:
            db.query(Feedback).filter(
                or_(Feedback.source_record_id.like("reportsapi-%"))
            ).delete(synchronize_session=False)
            db.commit()


def test_summary_param_guards(client: TestClient) -> None:
    """days sai giá trị → 422 (bộ lỗi chuẩn)."""
    auth = _login(client)
    assert client.get(
        "/api/reports/summary", params={"days": 15}, headers=auth
    ).status_code == 422


def test_summary_requires_auth(client: TestClient) -> None:
    """Guard router-level: client TƯƠI chưa login (cookie httpOnly từ test khác
    không dính vào đây vì fixture function-scoped) → 401."""
    assert client.get("/api/reports/summary").status_code == 401

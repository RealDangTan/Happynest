"""GET /api/feedbacks — filter `analysis_state` (pending | completed | uncategorized).

`uncategorized` thêm 2026-10-23 cho vòng taxonomy evolution trên vault: đếm
rows ĐÃ analyzed nhưng đang mang nhãn UNCATEGORIZED để gợi ý mở khoá re-enrich
sau khi taxonomy đổi. Marker `integration` — DB thật, không LLM.
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

SOURCE = "test-list-filter"


def _login(client: TestClient, account: str = "primary") -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[account], "password": TEST_PASSWORDS[account]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def filter_env(test_product):
    def _clean():
        with SessionLocal() as db:
            db.execute(delete(Feedback).where(Feedback.source == SOURCE))
            db.commit()

    _clean()
    yield test_product
    _clean()


def _seed(product_id: uuid.UUID, ref: str, analysis: dict | None) -> None:
    with SessionLocal() as db:
        kwargs = {"ai_analysis": analysis} if analysis is not None else {}
        # ⚠️ pending row = KHÔNG gửi key ai_analysis (SQL NULL). Gắn tường minh
        # `ai_analysis=None` qua ORM/psycopg3 lại ghi JSON `null` — không khớp
        # `IS NULL` (bug thật 2026-10-23, xem decisions.md).
        db.add(
            Feedback(
                product_id=product_id,
                source=SOURCE,
                source_record_id=ref,
                occurred_at=datetime.now(UTC),
                raw_content=f"noi dung gia {ref} (khong PII)",
                feedback_text=f"noi dung gia {ref}",
                **kwargs,
            )
        )
        db.commit()


def _seed_rich(
    product_id: uuid.UUID,
    ref: str,
    *,
    occurred_at: datetime,
    text: str,
    analysis: dict | None = None,
) -> None:
    """Seed có kiểm soát occurred_at + analysis cho test sort/search 2026-10-24."""
    with SessionLocal() as db:
        kwargs = {"ai_analysis": analysis} if analysis is not None else {}
        db.add(
            Feedback(
                product_id=product_id,
                source=SOURCE,
                source_record_id=ref,
                occurred_at=occurred_at,
                raw_content=f"{text} (khong PII)",
                feedback_text=text,
                **kwargs,
            )
        )
        db.commit()


def _refs(auth: dict, client: TestClient, product_id: uuid.UUID, qs: str) -> list[str]:
    resp = client.get(
        f"/api/feedbacks?limit=50&product_id={product_id}&{qs}", headers=auth
    )
    assert resp.status_code == 200, resp.text
    return [item["source_record_id"] for item in resp.json()["items"]]


def test_search_q_matches_text_and_source_case_insensitive(
    filter_env, client: TestClient
) -> None:
    """`q` search trên TOÀN BỘ tập dữ liệu (2026-10-24) — sửa bug FE search
    client-side từng trang: text + source, không phân biệt hoa thường."""
    auth = _login(client)
    pid = filter_env.id
    base = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)
    _seed_rich(pid, "pay-jpeg", occurred_at=base, text="payment loi khi upload jpeg", analysis={"topics": ["x"]})
    _seed_rich(pid, "slow", occurred_at=base, text="van toc cham qua", analysis={"topics": ["x"]})
    _seed_rich(pid, "src-hit", occurred_at=base, text="binh thuong", analysis={"topics": ["x"]})

    assert _refs(auth, client, pid, "q=payment") == ["pay-jpeg"]
    # Thuận ngữ search khớp cả cột source (SOURCE = "test-list-filter").
    # Cùng occurred_at → thứ tự theo id (UUID ngẫu nhiên): so sau khi sort.
    assert sorted(_refs(auth, client, pid, "q=TEST-LIST-FILTER")) == [
        "pay-jpeg",
        "slow",
        "src-hit",
    ]
    assert _refs(auth, client, pid, "q=khong-ton-tai") == []


def test_sort_whitelist_and_semantic_severity(
    filter_env, client: TestClient
) -> None:
    """`sort` whitelist (2026-10-24): severity theo thứ tự ngữ nghĩa
    low<medium<high<critical (không phải alphabet), confidence cast float,
    giá trị lạ → 422."""
    auth = _login(client)
    pid = filter_env.id
    base = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
    _seed_rich(pid, "sev-low", occurred_at=base, text="a", analysis={"severity": "low", "confidence": 0.9})
    _seed_rich(pid, "sev-critical", occurred_at=base, text="b", analysis={"severity": "critical", "confidence": 0.2})
    _seed_rich(pid, "sev-medium", occurred_at=base, text="c", analysis={"severity": "medium", "confidence": 0.5})
    _seed_rich(pid, "sev-none", occurred_at=base, text="d")  # chưa phân tích

    refs = _refs(auth, client, pid, "sort=severity")
    assert refs.index("sev-critical") < refs.index("sev-medium") < refs.index("sev-low")
    assert refs[-1] == "sev-none"  # chưa phân tích đứng cuối

    assert _refs(auth, client, pid, "sort=confidence")[0] == "sev-low"  # 0.9 cao nhất

    resp = client.get(
        f"/api/feedbacks?limit=50&product_id={pid}&sort=bogus", headers=auth
    )
    assert resp.status_code == 422


def _list(auth: dict, client: TestClient, product_id: uuid.UUID, state: str) -> list[str]:
    resp = client.get(
        f"/api/feedbacks?limit=50&product_id={product_id}&analysis_state={state}",
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    return [item["source_record_id"] for item in resp.json()["items"]]


def test_analysis_state_filters_partition_workspace(
    filter_env, client: TestClient
) -> None:
    auth = _login(client)
    pid = filter_env.id
    _seed(pid, "pending-row", None)
    _seed(pid, "uncat-row", {"topics": [], "uncategorized": True})
    _seed(pid, "done-row", {"topics": ["payment.payment_failure"], "uncategorized": False})

    assert _list(auth, client, pid, "pending") == ["pending-row"]
    assert sorted(_list(auth, client, pid, "uncategorized")) == ["uncat-row"]
    assert sorted(_list(auth, client, pid, "completed")) == ["done-row", "uncat-row"]

    # Giá trị lạ vẫn bị chặn ở schema (422) — không lộ rows.
    resp = client.get(
        f"/api/feedbacks?limit=50&product_id={pid}&analysis_state=bogus", headers=auth
    )
    assert resp.status_code == 422


def test_reset_uncategorized_writes_sql_null(
    filter_env, client: TestClient
) -> None:
    """Regression 2026-10-23: reset_uncategorized từng ghi JSON `null` (bind
    None qua psycopg3 JSONB) — row "Pending" trên FE nhưng `IS NULL` không khớp
    → vault đếm 0 pending, không chạy lại được. Phải là SQL NULL."""
    from sqlalchemy import select

    from app.services.analysis_service import reset_uncategorized

    auth = _login(client)
    pid = filter_env.id
    _seed(pid, "uncat-reset", {"topics": [], "uncategorized": True})
    _seed(pid, "keep-label", {"topics": ["x"], "uncategorized": False})

    released = reset_uncategorized(SessionLocal(), pid)
    assert released == 1

    with SessionLocal() as db:
        row = db.scalar(
            select(Feedback).where(
                Feedback.product_id == pid,
                Feedback.source_record_id == "uncat-reset",
                Feedback.ai_analysis.is_(None),  # SQL NULL thật
            )
        )
        assert row is not None, "reset phải ghi SQL NULL, không phải JSON null"
        assert row.analysis_run_id is None

    # Row đã reset lại đủ điều kiện pending cho run kế tiếp.
    assert _list(auth, client, pid, "pending") == ["uncat-reset"]

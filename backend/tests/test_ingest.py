"""Tests ingestion POST đơn lẻ — reshape VoC OS (plan 21) + plan 22.

⚠️ Marker `integration` — chạm DB Supabase DEV thật qua internet, chạy riêng:
`uv run pytest tests/test_ingest.py -m integration`

Phase 22: route `/feedbacks/import-csv` đã chuyển sang LISTEN pipeline
(`POST /api/imports` + Gate #1) — flow CSV test ở `test_imports_listen.py`.

Dọn dẹp: mọi row tạo ra bị xóa ở teardown qua fixture `clean_feedbacks`
(theo id hoặc source_record_id tiền tố `listtest-`) — không để rác trong DB
dev dùng chung.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import or_

from app.api.deps import require_role
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import UserRole
from app.models.feedback import Feedback
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------- helpers


def _login_headers(client, role: UserRole) -> dict[str, str]:
    """Login lấy JWT rồi dùng Bearer header (đường song song cookie, Phase 04)."""
    response = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def clean_feedbacks():
    """Thu id các row test tạo; teardown xóa cả theo id lẫn theo tiền tố
    source_record_id của test — kể từ lần chạy trước nếu còn sót."""
    ids: list[uuid.UUID] = []
    yield ids
    prefixes = ["listtest-"]
    with SessionLocal() as db:
        db.query(Feedback).filter(
            or_(
                Feedback.id.in_(ids or [uuid.uuid4()]),  # in_([]) là no-op an toàn hơn nhưng vẫn rõ ý
                *[Feedback.source_record_id.like(f"{p}%") for p in prefixes],
            )
        ).delete(synchronize_session=False)
        db.commit()


# ------------------------------------------------------------------- POST


class TestPostSingle:
    def test_stores_fields_and_fallback_occurred_at(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.pm)
        content = "Ứng dụng hay nhưng hay lag khi dịch"
        before = datetime.now(timezone.utc)
        response = client.post(
            "/api/feedbacks",
            json={"source": "app_review", "content": content},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        # Ranh giới PII: response KHÔNG BAO GIỜ chứa raw_content (kể cả detail)
        assert "raw_content" not in body
        # sanitize chạy ngay lúc ingest; text sạch → pass-through
        assert body["feedback_text"] == content
        assert body["pii_detected"] is False
        assert body["ai_analysis"] is None
        assert body["data"] == {} and body["source_meta"] == {}
        clean_feedbacks.append(uuid.UUID(body["id"]))

        with SessionLocal() as db:
            row = db.get(Feedback, uuid.UUID(body["id"]))
            assert row.raw_content == content  # lưu nguyên vẹn (DoD mục 3)
            assert row.feedback_text == content
            # occurred_at thiếu → event time = now() lúc ingest (+dung sai WAN)
            delta = abs((row.occurred_at - before).total_seconds())
            assert delta < 180, f"occurred_at lệch {delta}s"
            assert row.imported_at is not None
            assert row.product_id is not None  # gắn product mặc định
            assert row.import_id is None  # POST đơn lẻ không qua import lô

    def test_preserves_explicit_event_time(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.operations)
        event_time = "2025-01-15T10:00:00+00:00"
        response = client.post(
            "/api/feedbacks",
            json={
                "source": "survey",
                "content": "x",
                "occurred_at": event_time,
                "source_record_id": "listtest-explicit-time",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        fid = uuid.UUID(response.json()["id"])
        clean_feedbacks.append(fid)

        with SessionLocal() as db:
            row = db.get(Feedback, fid)
            assert row.occurred_at == datetime.fromisoformat(event_time)
            assert row.source_record_id == "listtest-explicit-time"


# ------------------------------------------------------------ list + detail


def _make_rows(client, headers, clean_feedbacks, n=3):
    """Tạo n feedback gắn topic độc lập 'listtest-cat' để filter không đụng
    data thật trong DB dev."""
    ids = []
    for i in range(n):
        response = client.post(
            "/api/feedbacks",
            json={
                "source": "in_app_form",
                "content": f"row test filter {i}",
                "source_record_id": f"listtest-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        fid = uuid.UUID(response.json()["id"])
        clean_feedbacks.append(fid)
        ids.append(fid)
    return ids


class TestListAndDetail:
    def test_pagination_and_filters(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.pm)
        ids = _make_rows(client, headers, clean_feedbacks, n=3)

        # Mô phỏng hậu classify: severity/topics nằm trong ai_analysis JSONB —
        # ingestion để NULL nên phải set trực tiếp DB. Cả 3 row cùng topic để
        # filter cô lập chúng khỏi data thật.
        with SessionLocal() as db:
            for fid in ids:
                db.get(Feedback, fid).ai_analysis = {
                    "topics": ["listtest-cat"],
                    "sentiment": "negative",
                    "severity": "medium",
                }
            db.get(Feedback, ids[0]).ai_analysis = {
                **db.get(Feedback, ids[0]).ai_analysis,
                "severity": "critical",
            }
            db.commit()

        base = {"topic": "listtest-cat"}
        full = client.get("/api/feedbacks", params=base, headers=headers).json()
        assert full["total"] == 3 and len(full["items"]) == 3

        paged = client.get(
            "/api/feedbacks", params={**base, "limit": 2, "offset": 0}, headers=headers
        ).json()
        assert paged["total"] == 3 and len(paged["items"]) == 2 and paged["limit"] == 2
        tail = client.get(
            "/api/feedbacks", params={**base, "limit": 2, "offset": 2}, headers=headers
        ).json()
        assert len(tail["items"]) == 1

        sev = client.get(
            "/api/feedbacks", params={**base, "severity": "critical"}, headers=headers
        ).json()
        assert sev["total"] == 1 and sev["items"][0]["id"] == str(ids[0])

        sen = client.get(
            "/api/feedbacks", params={**base, "sentiment": "negative"}, headers=headers
        ).json()
        assert sen["total"] == 3

    def test_limit_over_100_rejected(self, client):
        headers = _login_headers(client, UserRole.pm)
        response = client.get("/api/feedbacks", params={"limit": 101}, headers=headers)
        assert response.status_code == 422

    def test_detail_never_exposes_raw(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.pm)
        content = "SĐT tôi là 0987654321, đừng lộ"
        fid = uuid.UUID(
            client.post(
                "/api/feedbacks",
                json={"source": "email", "content": content},
                headers=headers,
            ).json()["id"]
        )
        clean_feedbacks.append(fid)

        safe = client.get(f"/api/feedbacks/{fid}", headers=headers).json()
        assert "raw_content" not in safe
        assert safe["feedback_text"] != content  # đã sanitize
        assert "0987654321" not in safe["feedback_text"]

    def test_detail_404_unknown_id(self, client):
        headers = _login_headers(client, UserRole.pm)
        missing = uuid.uuid4()
        response = client.get(f"/api/feedbacks/{missing}", headers=headers)
        assert response.status_code == 404


# ------------------------------------------------------------------ guard


class TestRoleGuard:
    def test_anonymous_rejected_both_roles_allowed_then_403_on_pm_only_route(
        self, client, clean_feedbacks
    ):
        # Vô danh → 401 (chưa xác thực, khác 403)
        response = client.post(
            "/api/feedbacks", json={"source": "s", "content": "c"}
        )
        assert response.status_code == 401

        # Cả hai role seeded đều được phép ingestion
        ops_headers = _login_headers(client, UserRole.operations)
        response = client.post(
            "/api/feedbacks",
            json={"source": "s", "content": "ops được phép"},
            headers=ops_headers,
        )
        assert response.status_code == 201
        clean_feedbacks.append(uuid.UUID(response.json()["id"]))

        # 403: RBAC universe chỉ có pm|operations (đều được phép trên route
        # thật) nên tái hiện đúng precedent phase 04 — mount route pm-only tạm.
        routes_before = len(app.routes)
        demo = APIRouter()

        # Path 2 segment để KHÔNG bị nuốt bởi pattern `/feedbacks/{id}`
        # (1 segment, UUID-typed → sẽ 422 trước khi tới route tạm).
        @demo.get("/api/feedbacks/_guard/demo")
        def guard_demo(user=Depends(require_role("pm"))):  # noqa: F821
            return {"ok": True}

        app.include_router(demo)
        try:
            forbidden = client.get("/api/feedbacks/_guard/demo", headers=ops_headers)
            assert forbidden.status_code == 403
        finally:
            del app.routes[routes_before:]

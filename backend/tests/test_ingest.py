"""Tests ingestion Phase 05 (05-feedback-ingestion.md §3.5).

⚠️ Marker `integration` — chạm DB Supabase DEV thật qua internet, chạy riêng:
`uv run pytest tests/test_ingest.py -m integration`
(quy ước marker do phase 08 thiết lập trong pyproject: mặc định `-m 'not integration'`).

Dọn dẹp: mọi row tạo ra bị xóa ở teardown qua fixture `clean_feedbacks`
(theo id hoặc external_ref tiền tố `fixture20-`/`badcsv-`) — không để rác
trong DB dev dùng chung.
"""

import csv
import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import or_

from app.api.deps import require_role
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import ReviewStatus, Severity, UserRole
from app.models.feedback import Feedback
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

FIXTURE_CSV = "tests/fixtures/feedback_sample_20.csv"


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
    external_ref của fixture/bad-csv — kể từ lần chạy trước nếu còn sót."""
    ids: list[uuid.UUID] = []
    yield ids
    prefixes = ["fixture20-", "badcsv-", "listtest-"]
    with SessionLocal() as db:
        db.query(Feedback).filter(
            or_(
                Feedback.id.in_(ids or [uuid.uuid4()]),  # in_([]) là no-op an toàn hơn nhưng vẫn rõ ý
                *[Feedback.external_ref.like(f"{p}%") for p in prefixes],
            )
        ).delete(synchronize_session=False)
        db.commit()


# ------------------------------------------------------------------- POST


class TestPostSingle:
    def test_stores_fields_and_fallback_created_at(self, client, clean_feedbacks):
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
        # Ranh giới PII: response mặc định KHÔNG chứa raw_content
        assert "raw_content" not in body
        # Phase 06: sanitize chạy ngay lúc ingest; text sạch → pass-through.
        assert body["sanitized_content"] == content
        assert body["pii_detected"] is False
        assert body["severity"] is None and body["categories"] is None
        assert body["review_status"] == "unreviewed"
        assert body["requires_human_review"] is False
        clean_feedbacks.append(uuid.UUID(body["id"]))

        with SessionLocal() as db:
            row = db.get(Feedback, uuid.UUID(body["id"]))
            assert row.raw_content == content  # lưu nguyên vẹn (DoD mục 3)
            assert row.sanitized_content == content
            # created_at thiếu → event time = now() lúc ingest (+dung sai WAN)
            delta = abs((row.created_at - before).total_seconds())
            assert delta < 180, f"created_at lệch {delta}s"
            assert row.imported_at is not None

    def test_preserves_explicit_event_time(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.operations)
        event_time = "2025-01-15T10:00:00+00:00"
        response = client.post(
            "/api/feedbacks",
            json={"source": "survey", "content": "x", "created_at": event_time},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        fid = uuid.UUID(response.json()["id"])
        clean_feedbacks.append(fid)

        with SessionLocal() as db:
            row = db.get(Feedback, fid)
            assert row.created_at == datetime.fromisoformat(event_time)


# --------------------------------------------------------------- import-csv


class TestImportCsv:
    def test_full_fixture_20_rows(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.pm)
        with open(FIXTURE_CSV, "rb") as f:
            response = client.post(
                "/api/feedbacks/import-csv",
                files={"file": ("feedback_sample_20.csv", f, "text/csv")},
                headers=headers,
            )
        assert response.status_code == 200, response.text
        report = response.json()
        assert report["imported"] == 20
        assert report["failed"] == 0 and report["errors"] == []

        with SessionLocal() as db:
            count = (
                db.query(Feedback)
                .filter(Feedback.external_ref.like("fixture20-%"))
                .count()
            )
            assert count == 20
            # UTF-8/BOM: dấu tiếng Việt không hỏng (DoD mixed VN-EN)
            row = (
                db.query(Feedback)
                .filter(Feedback.external_ref == "fixture20-02")
                .one()
            )
            assert "Nguyễn Văn An" in row.raw_content
            # created_at từ cột CSV được tôn trọng (event time, có offset +07:00)
            assert row.created_at.utcoffset() is not None

    def test_bad_rows_counted_not_aborted(self, client, clean_feedbacks):
        headers = _login_headers(client, UserRole.pm)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["source", "content", "external_ref", "created_at"])
        writer.writerow(["survey", "dòng hợp lệ 1", "badcsv-1", "2026-01-01T00:00:00+00:00"])
        writer.writerow(["", "thiếu source", "badcsv-x", ""])  # dòng 3 lỗi
        writer.writerow(["email", "ngày sai format", "badcsv-y", "01/02/2026"])  # dòng 4 lỗi
        writer.writerow(["app_review", "dòng hợp lệ 2", "badcsv-2", ""])

        response = client.post(
            "/api/feedbacks/import-csv",
            files={"file": ("messy.csv", buffer.getvalue().encode(), "text/csv")},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        report = response.json()
        assert report["imported"] == 2
        assert report["failed"] == 2
        assert {e["row"] for e in report["errors"]} == {3, 4}
        assert all(e["reason"] for e in report["errors"])

        with SessionLocal() as db:
            kept = (
                db.query(Feedback)
                .filter(Feedback.external_ref.like("badcsv-%"))
                .count()
            )
            assert kept == 2  # dòng lỗi không cản dòng hợp lệ

    def test_non_csv_extension_rejected(self, client):
        headers = _login_headers(client, UserRole.pm)
        response = client.post(
            "/api/feedbacks/import-csv",
            files={"file": ("not_csv.txt", b"hello", "text/plain")},
            headers=headers,
        )
        assert response.status_code == 422


# ------------------------------------------------------------ list + detail


def _make_rows(client, headers, clean_feedbacks, n=3):
    """Tạo n feedback gắn category độc lập 'listtest-cat' để filter không đụng
    data thật trong DB dev."""
    ids = []
    for i in range(n):
        response = client.post(
            "/api/feedbacks",
            json={
                "source": "in_app_form",
                "content": f"row test filter {i}",
                "external_ref": f"listtest-{uuid.uuid4().hex[:8]}",
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

        # Mô phỏng hậu classify: severity/categories/review_status là cột
        # Phase 07/HITL điền — ingestion để NULL nên phải set trực tiếp DB.
        # Cả 3 row cùng category để filter category cô lập chúng khỏi data thật.
        with SessionLocal() as db:
            for fid in ids:
                db.get(Feedback, fid).categories = ["listtest-cat"]
            db.get(Feedback, ids[0]).severity = Severity.critical
            db.get(Feedback, ids[1]).review_status = ReviewStatus.approved
            db.commit()

        base = {"category": "listtest-cat"}
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

        status_filter = client.get(
            "/api/feedbacks",
            params={**base, "review_status": "approved"},
            headers=headers,
        ).json()
        assert status_filter["total"] == 1 and status_filter["items"][0]["id"] == str(ids[1])

    def test_limit_over_100_rejected(self, client):
        headers = _login_headers(client, UserRole.pm)
        response = client.get("/api/feedbacks", params={"limit": 101}, headers=headers)
        assert response.status_code == 422

    def test_detail_hides_raw_by_default(self, client, clean_feedbacks):
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

        with_raw = client.get(
            f"/api/feedbacks/{fid}", params={"include_raw": "true"}, headers=headers
        ).json()
        assert with_raw["raw_content"] == content

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

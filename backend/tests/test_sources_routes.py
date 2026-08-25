"""Sources registry tests — FE-03b (docs/plans/FE-03b-source-columns-csv-map.md T1).

⚠️ Marker `integration` — chạm DB Supabase thật qua fixture `client`/seed users.
Tên nguồn dùng uuid suffix để chạy lại không đụng 409 với row lần trước.
"""

import uuid

import pytest

from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _login(client):
    resp = client.post(
        "/api/auth/token",
        data={
            "username": SEED_EMAILS["pm"],
            "password": TEST_PASSWORDS["pm"],
        },
    )
    assert resp.status_code == 200
    return resp


def _unique_name() -> str:
    return f"test-src-{uuid.uuid4().hex[:8]}"


class TestSourcesCrud:
    def test_create_and_list_contains(self, client):
        _login(client)
        name = _unique_name()
        created = client.post(
            "/api/sources", json={"name": name, "description": "mô tả test"}
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == name
        assert body["description"] == "mô tả test"
        assert body["is_active"] is True
        assert body["id"] and body["created_at"]

        listed = client.get("/api/sources")
        assert listed.status_code == 200
        names = [s["name"] for s in listed.json()]
        assert name in names

    def test_duplicate_name_409(self, client):
        _login(client)
        payload = {"name": _unique_name()}
        first = client.post("/api/sources", json=payload)
        assert first.status_code == 201
        dup = client.post("/api/sources", json=payload)
        assert dup.status_code == 409
        assert "đã tồn tại" in dup.json()["detail"]

    def test_patch_toggle_is_active(self, client):
        _login(client)
        name = _unique_name()
        sid = client.post("/api/sources", json={"name": name}).json()["id"]

        off = client.patch(f"/api/sources/{sid}", json={"is_active": False})
        assert off.status_code == 200
        assert off.json()["is_active"] is False

        # List vẫn trả inactive (UI tự lọc theo flag).
        listed = client.get("/api/sources").json()
        row = next(s for s in listed if s["id"] == sid)
        assert row["is_active"] is False

    def test_patch_unknown_id_404(self, client):
        _login(client)
        missing = str(uuid.uuid4())
        resp = client.patch(f"/api/sources/{missing}", json={"is_active": False})
        assert resp.status_code == 404

    def test_anon_401(self, client):
        client.cookies.clear()
        assert client.get("/api/sources").status_code == 401

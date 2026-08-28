"""Auth & RBAC tests — Phase 04 (docs/plans/04-auth-rbac.md §3.6).

⚠️ Marker `integration` — chạm DB Supabase thật qua fixture `client`/`seeded_users`
(cần .env + internet). Marker bổ sung Phase 11: từ Phase 04 file này thiếu marker
nên 12 test auth lọt vào unit suite mặc định — phát hiện khi rà soát plan 11 §3.2.
"""

import uuid

import pytest

from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

PM_EMAIL = SEED_EMAILS["pm"]
OPS_EMAIL = SEED_EMAILS["operations"]


def _unique_email() -> str:
    """Email duy nhất mỗi run — integration test chạm DB thật, không dọn row."""
    return f"reg-{uuid.uuid4().hex[:10]}@thesis.local"


def _login(client, email: str, password: str):
    return client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
    )


class TestLogin:
    def test_login_success_returns_body_and_cookie(self, client):
        resp = _login(client, PM_EMAIL, TEST_PASSWORDS["pm"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

        set_cookie = resp.headers["set-cookie"]
        assert "HttpOnly" in set_cookie
        assert "samesite=lax" in set_cookie.lower()
        assert "Path=/" in set_cookie
        assert "Secure" not in set_cookie  # dev → secure=False

    def test_login_operations_role_ok(self, client):
        """DoD 04: login cả 2 role seeded thành công."""
        resp = _login(client, OPS_EMAIL, TEST_PASSWORDS["operations"])
        assert resp.status_code == 200

    def test_login_wrong_password_401(self, client):
        resp = _login(client, PM_EMAIL, "mat-khau-sai-roang")
        assert resp.status_code == 401

    def test_login_unknown_email_401_same_detail(self, client):
        """Không tiết lộ email có tồn tại hay không (user enumeration)."""
        wrong_pass = _login(client, PM_EMAIL, "wrong-pass")
        unknown = _login(client, "khongtontai@thesis.local", "whatever-pass")
        assert unknown.status_code == 401
        assert unknown.json()["detail"] == wrong_pass.json()["detail"]


class TestMe:
    def test_me_with_cookie(self, client):
        login = _login(client, PM_EMAIL, TEST_PASSWORDS["pm"])
        token = login.json()["access_token"]

        me = client.get("/api/auth/me", cookies={"access_token": token})
        assert me.status_code == 200
        data = me.json()
        assert data["email"] == PM_EMAIL
        assert data["role"] == "pm"
        assert data["id"]

    def test_me_with_bearer_header(self, client):
        """Cơ chế song song Bearer (decisions.md 2026-08-24) — Swagger/curl dùng."""
        login = _login(client, OPS_EMAIL, TEST_PASSWORDS["operations"])
        token = login.json()["access_token"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["role"] == "operations"

    def test_me_without_credentials_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_with_garbage_token_401(self, client):
        me = client.get("/api/auth/me", cookies={"access_token": "not-a-jwt"})
        assert me.status_code == 401

    def test_me_with_tampered_token_401(self, client):
        from app.core.security import create_access_token

        tampered = (
            create_access_token(
                sub="00000000-0000-0000-0000-000000000000", role="pm"
            )
            + "x"
        )
        me = client.get("/api/auth/me", cookies={"access_token": tampered})
        assert me.status_code == 401


class TestRegister:
    """P1.5 / FE-08 — POST /api/auth/register, role mặc định `operations`."""

    def test_register_creates_operations_user_201(self, client):
        email = _unique_email()
        resp = client.post(
            "/api/auth/register", json={"email": email, "password": "mat-khau-8kt"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email
        assert data["role"] == "operations"
        assert data["id"]

    def test_register_then_login_ok(self, client):
        """Đăng ký xong login được ngay bằng chính thông tin vừa đăng ký."""
        email = _unique_email()
        client.post(
            "/api/auth/register", json={"email": email, "password": "mat-khau-8kt"}
        )
        resp = _login(client, email, "mat-khau-8kt")
        assert resp.status_code == 200

    def test_register_normalizes_email_lowercase(self, client):
        email = _unique_email()
        client.post(
            "/api/auth/register",
            json={"email": email.upper(), "password": "mat-khau-8kt"},
        )
        resp = _login(client, email, "mat-khau-8kt")
        assert resp.status_code == 200

    def test_register_duplicate_email_409(self, client):
        resp = client.post(
            "/api/auth/register", json={"email": PM_EMAIL, "password": "mat-khau-8kt"}
        )
        assert resp.status_code == 409

    def test_register_short_password_422(self, client):
        resp = client.post(
            "/api/auth/register", json={"email": _unique_email(), "password": "ngan"}
        )
        assert resp.status_code == 422

    def test_register_bad_email_422(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "khong-phai-email", "password": "mat-khau-8kt"},
        )
        assert resp.status_code == 422


class TestLogout:
    """P1.5 / FE-08 — POST /api/auth/logout xoá cookie httpOnly."""

    def test_logout_clears_cookie_204(self, client):
        login = _login(client, PM_EMAIL, TEST_PASSWORDS["pm"])
        assert "access_token" in client.cookies

        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204
        set_cookie = resp.headers["set-cookie"]
        assert "access_token=" in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    def test_logout_without_session_ok(self, client):
        """Idempotent — gọi khi chưa login vẫn 204."""
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204


class TestRoleGuard:
    """Route guard demo — route pm-only gắn tạm trong fixture pm_guarded_client."""

    def test_pm_allowed_on_pm_only_route(self, pm_guarded_client):
        login = _login(pm_guarded_client, PM_EMAIL, TEST_PASSWORDS["pm"])
        token = login.json()["access_token"]
        resp = pm_guarded_client.get(
            "/api/auth/_guard-demo", cookies={"access_token": token}
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_operations_gets_403_on_pm_only_route(self, pm_guarded_client):
        """DoD 04: route guarded trả 403 với role sai."""
        login = _login(pm_guarded_client, OPS_EMAIL, TEST_PASSWORDS["operations"])
        token = login.json()["access_token"]
        resp = pm_guarded_client.get(
            "/api/auth/_guard-demo", cookies={"access_token": token}
        )
        assert resp.status_code == 403

    def test_anonymous_gets_401_not_403(self, pm_guarded_client):
        resp = pm_guarded_client.get("/api/auth/_guard-demo")
        assert resp.status_code == 401

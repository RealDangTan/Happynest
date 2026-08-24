"""Auth & RBAC tests — Phase 04 (docs/plans/04-auth-rbac.md §3.6).

Chạy trên DB Supabase DEV thật (xem conftest) — cần .env + internet.
"""

from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

PM_EMAIL = SEED_EMAILS["pm"]
OPS_EMAIL = SEED_EMAILS["operations"]


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

"""Google OAuth login tests — flow login/callback + upsert/link account.

⚠️ Marker `integration` — chạm DB Supabase thật qua fixture `client`
(giống test_auth.py). Google exchange/verify được MONKEYPATCH ở tầng
`app.services.google_oauth` nên test KHÔNG chạm mạng Google; phần thật của
flow (redirect, state cookie, upsert/link, JWT cookie) chạy đầy đủ.

Email dùng `@thesis.local` duy nhất mỗi run — integration test không dọn row
(cùng convention test_auth.py), không chứa PII.
"""

import uuid

import pytest

from app.services import google_oauth
from tests.conftest import TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"google-{uuid.uuid4().hex[:10]}@thesis.local"


@pytest.fixture
def google_settings(monkeypatch):
    """Bật cấu hình Google trên settings instance (đã cache) — restore tự động."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(
        settings,
        "GOOGLE_REDIRECT_URI",
        "http://testserver/api/auth/google/callback",
    )
    return settings


@pytest.fixture
def fake_google(monkeypatch):
    """Thay exchange/verify bằng claims giả — khung flow thật vẫn chạy."""
    claims: dict = {}

    def _set_claims(**kwargs) -> None:
        claims.clear()
        claims.update(kwargs)

    monkeypatch.setattr(google_oauth, "exchange_code", lambda code: f"fake-id-token:{code}")
    monkeypatch.setattr(google_oauth, "verify_id_token", lambda id_token: dict(claims))
    return _set_claims


def _finish_callback(client) -> object:
    """Đi trọn flow: /google/login → callback với code + state cookie thật."""
    login = client.get("/api/auth/google/login", follow_redirects=False)
    assert login.status_code == 302
    state = login.cookies.get(google_oauth.STATE_COOKIE)
    assert state, "state cookie phải được set ở bước login"
    callback = client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert (
        "google_error" not in callback.headers.get("location", "")
    ), f"callback lỗi: {callback.headers.get('location')}"
    return callback


class TestGoogleLogin:
    def test_disabled_by_default_503(self, client):
        """Mặc định .env không có GOOGLE_* → 503 kèm thông báo rõ."""
        resp = client.get("/api/auth/google/login")
        assert resp.status_code == 503
        assert "GOOGLE_CLIENT_ID" in resp.json()["detail"]

    def test_redirects_to_google_with_state_cookie(self, client, google_settings):
        resp = client.get("/api/auth/google/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "client_id=test-client-id" in resp.headers["location"]
        assert "redirect_uri=http" in resp.headers["location"]

        set_cookie = resp.headers["set-cookie"]
        assert "g_oauth_state=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/api/auth/google" in set_cookie


class TestGoogleCallback:
    def test_denied_redirects_to_login(self, client, google_settings):
        resp = client.get(
            "/api/auth/google/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login?google_error=denied" in resp.headers["location"]

    def test_state_mismatch_redirects(self, client, google_settings):
        resp = client.get(
            "/api/auth/google/callback",
            params={"code": "abc", "state": "khong-khop"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "google_error=state" in resp.headers["location"]
        assert "access_token" not in resp.headers.get("set-cookie", "")

    def test_creates_google_only_account_and_logs_in(
        self, client, google_settings, fake_google
    ):
        email = _unique_email()
        fake_google(sub="google-sub-" + uuid.uuid4().hex[:8], email=email, email_verified=True)

        callback = _finish_callback(client)
        assert callback.status_code == 302
        assert callback.headers["location"] == "/"

        # JWT cookie hợp lệ → /me trả đúng identity mới.
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_links_existing_password_account(self, client, google_settings, fake_google):
        """Email đã đăng ký password → Google login LINK, không tạo user mới."""
        email = _unique_email()
        reg = client.post(
            "/api/auth/register", json={"email": email, "password": "mat-khau-8kt"}
        )
        user_id = reg.json()["id"]

        fake_google(sub="google-sub-" + uuid.uuid4().hex[:8], email=email, email_verified=True)
        callback = _finish_callback(client)
        assert callback.status_code == 302

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == user_id  # cùng user, không nhân bản

        # Mật khẩu cũ vẫn dùng được sau khi link.
        client.post("/api/auth/logout")
        login = client.post(
            "/api/auth/token",
            data={"username": email, "password": "mat-khau-8kt"},
        )
        assert login.status_code == 200

    def test_second_google_login_reuses_same_user(
        self, client, google_settings, fake_google
    ):
        sub = "google-sub-" + uuid.uuid4().hex[:8]
        email = _unique_email()
        fake_google(sub=sub, email=email, email_verified=True)
        _finish_callback(client)
        first_id = client.get("/api/auth/me").json()["id"]

        client.post("/api/auth/logout")
        _finish_callback(client)
        assert client.get("/api/auth/me").json()["id"] == first_id

    def test_unverified_email_rejected(self, client, google_settings, fake_google):
        fake_google(
            sub="google-sub-" + uuid.uuid4().hex[:8],
            email=_unique_email(),
            email_verified=False,
        )
        # Flow này CHỦ ĐÍCH kết thúc bằng redirect lỗi — đi 2 bước thủ công
        # vì helper _finish_callback chặn callback có google_error.
        login = client.get("/api/auth/google/login", follow_redirects=False)
        state = login.cookies.get(google_oauth.STATE_COOKIE)
        callback = client.get(
            "/api/auth/google/callback",
            params={"code": "abc", "state": state},
            follow_redirects=False,
        )
        assert callback.status_code == 302
        assert "google_error=exchange" in callback.headers["location"]


class TestGoogleOnlyAccountGuards:
    def test_password_login_google_only_distinct_401(
        self, client, google_settings, fake_google
    ):
        email = _unique_email()
        fake_google(sub="google-sub-" + uuid.uuid4().hex[:8], email=email, email_verified=True)
        _finish_callback(client)
        client.post("/api/auth/logout")

        resp = client.post(
            "/api/auth/token",
            data={"username": email, "password": "dung-thu-mat-khau"},
        )
        assert resp.status_code == 401
        assert "Google" in resp.json()["detail"]

    def test_register_google_only_email_409(self, client, google_settings, fake_google):
        email = _unique_email()
        fake_google(sub="google-sub-" + uuid.uuid4().hex[:8], email=email, email_verified=True)
        _finish_callback(client)
        client.post("/api/auth/logout")

        resp = client.post(
            "/api/auth/register", json={"email": email, "password": "mat-khau-8kt"}
        )
        assert resp.status_code == 409
        assert "Google" in resp.json()["detail"]


class TestExtractIdentity:
    """Phần thuần function — không DB, không mạng."""

    def test_ok_normalizes_email(self):
        identity = google_oauth.extract_identity(
            {"sub": "sub-1", "email": "A@Example.COM", "email_verified": True}
        )
        assert identity.email == "a@example.com"
        assert identity.google_sub == "sub-1"

    def test_missing_email_raises(self):
        with pytest.raises(ValueError):
            google_oauth.extract_identity({"sub": "sub-1", "email_verified": True})

    def test_unverified_email_raises(self):
        with pytest.raises(ValueError):
            google_oauth.extract_identity(
                {"sub": "sub-1", "email": "a@b.co", "email_verified": False}
            )

"""Google OAuth 2.0 Authorization Code flow — đăng nhập bằng tài khoản Google.

Thiết kế (decisions.md 2026-10-23):
- Authorization Code flow thuần theo RFC 6749 + OpenID Connect Core: 302 →
  accounts.google.com → callback nhận `?code` → đổi token tại
  oauth2.googleapis.com/token → verify `id_token` (RS256, JWKS Google).
- KHÔNG thêm authlib/google-auth vào locked stack: PyJWT (đã có) tự verify
  RS256 qua `jwt.PyJWKClient`; httpx (đã có gián tiếp qua openai SDK, giờ khai
  báo tường minh trong pyproject) dùng cho token exchange.
- Chỉ dùng `id_token` (bỏ qua access_token + userinfo endpoint) — đủ
  email/sub cho identity-only auth, ít một request mạng.
- Mọi lỗi (state sai, exchange lỗi, token sai) đều callback redirect về FE
  `?google_error=<mã>` thay vì raise — user thấy trang login kèm alert.
"""

from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"

# Session state chống CSRF: cookie ngắn hạn, scope chặt đúng 2 route Google.
STATE_COOKIE = "g_oauth_state"
STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class GoogleIdentity:
    """Bản sắc tối thiểu lấy từ id_token — khớp contract user identity."""

    google_sub: str
    email: str


def google_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and settings.GOOGLE_REDIRECT_URI
    )


def build_authorization_url(state: str) -> str:
    """URL trang chọn tài khoản Google; scope openid giữ payload nhỏ."""
    settings = get_settings()
    params = httpx.QueryParams(
        {
            "response_type": "code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            # Buộc hiện màn chọn account ngay cả khi đã có session Google —
            # máy dùng chung cho nhiều account workspace.
            "prompt": "select_account",
        }
    )
    return f"{_AUTH_ENDPOINT}?{params}"


def exchange_code(code: str) -> str:
    """Đổi authorization code lấy id_token; raise httpx/ValueError khi lỗi."""
    settings = get_settings()
    resp = httpx.post(
        _TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
        },
        timeout=15.0,
    )
    if resp.status_code != 200:
        # Không log body (có thể chứa token) — chỉ status cho đủ debug.
        logger.warning("google token exchange failed status=%s", resp.status_code)
        raise ValueError(f"token exchange HTTP {resp.status_code}")
    id_token = resp.json().get("id_token")
    if not id_token:
        raise ValueError("token response thiếu id_token")
    return id_token


def verify_id_token(id_token: str, jwks_client: PyJWKClient | None = None) -> dict:
    """Verify chữ ký RS256 qua JWKS Google + aud/iss/exp; trả claims.

    `jwks_client` cho phép tiêm bản giả lập trong test (không chạm mạng).
    """
    settings = get_settings()
    client = jwks_client or PyJWKClient(_JWKS_URI)
    signing_key = client.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.GOOGLE_CLIENT_ID,
        issuer=["https://accounts.google.com", "accounts.google.com"],
    )


def extract_identity(claims: dict) -> GoogleIdentity:
    """Lấy (sub, email) từ claims; từ chối khi email thiếu hoặc chưa verify."""
    email = claims.get("email")
    sub = claims.get("sub")
    if not sub or not email:
        raise ValueError("id_token thiếu sub/email")
    if not claims.get("email_verified", False):
        raise ValueError("email Google chưa được verify")
    return GoogleIdentity(google_sub=sub, email=str(email).strip().lower())

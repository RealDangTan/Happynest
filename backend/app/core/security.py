"""Hash mật khẩu + JWT — Phase 04 (docs/plans/04-auth-rbac.md §3.1).

Locked stack (AGENTS.md): argon2 qua `pwdlib[argon2]`, HS256 qua PyJWT,
token sống 12h, claim `sub` = user id (UUID dạng string), `role`.
"""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# pwdlib.recommended() = Argon2Hash khi cài extras [argon2] — đúng locked stack.
_password_hasher = PasswordHash.recommended()

ACCESS_TOKEN_TTL_HOURS = 12  # đổi giá trị này nếu cần dài/ngắn hơn (plan §6)
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Argon2 hash — DB chỉ lưu output này (prefix `$argon2`)."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext chống lại hash đã lưu."""
    return _password_hasher.verify(password, password_hash)


def create_access_token(sub: str, role: str) -> str:
    """HS256 JWT: sub = user id, role, iat, exp = now + TTL.

    SECRET_KEY bắt buộc (config.py ghi chú enforce từ Phase 04) — chặn sớm với
    thông báo rõ thay vì ký token bằng chuỗi rỗng.
    """
    settings = get_settings()
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY chưa đặt — không thể ký JWT. Điền SECRET_KEY vào backend/.env "
            "(ví dụ: openssl rand -hex 32)."
        )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode + verify chữ ký/exp; raise jwt.PyJWTError cho caller bắt (deps)."""
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])

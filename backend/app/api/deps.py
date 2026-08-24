"""Dependencies dùng chung cho routes — Phase 04 hoàn thiện (04-auth-rbac.md §3.3).

Lịch sử file: Phase 08 (thực thi trước 04 theo quyết định owner — xem
docs/decisions.md 2026-08-24) dựng scaffold với `get_db`; Phase 04 MỞ RỘNG
(không viết lại) với cơ chế auth: cookie httpOnly ưu tiên, fallback Bearer
header cho Swagger/curl/test (entry riêng trong decisions.md cùng ngày).
"""

import uuid
from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

COOKIE_NAME = "access_token"  # trùng field OAuth2 mặc định để Swagger Authorize khớp


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: 1 session per request, đóng chắc chắn sau response."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """Đọc token từ cookie trước; không có → rơi về hành vi gốc (Bearer header,
    tự raise 401 kèm WWW-Authenticate khi thiếu hoàn toàn)."""

    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            return token
        return await super().__call__(request)


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT → load user theo id; 401 cho mọi trường hợp hỏng
    (token sai/hết hạn, sub không parse được UUID, user đã bị xóa)."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không xác thực được — token thiếu, sai hoặc đã hết hạn.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_error from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_role(*roles: str):
    """Factory dependency: chặn role ngoài danh sách bằng 403.

    Dùng: `Depends(require_role("pm", "operations"))`.
    """

    allowed = set(roles)

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' không có quyền truy cập tài nguyên này.",
            )
        return user

    return checker

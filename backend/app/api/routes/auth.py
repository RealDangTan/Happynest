"""Auth routes — Phase 04 (docs/plans/04-auth-rbac.md §3.4).

OAuth2 password flow do FastAPI sở hữu; JWT nằm trong cookie httpOnly
SameSite=Lax. REGISTER DISABLED — không có route đăng ký công khai; user chỉ
được tạo bởi `scripts/seed_users.py` (2 tài khoản seed).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, get_current_user, get_db
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import TokenOut, UserOut

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 401 chung — không tiết lộ email có tồn tại hay không (user enumeration).
_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email hoặc mật khẩu không đúng.",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/token", response_model=TokenOut)
def login_for_access_token(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenOut:
    """Đăng nhập (username == email) → set cookie + trả body TokenOut.

    Cookie name `access_token` trùng field OAuth2 mặc định để Swagger
    "Authorize" hoạt động được với cookie.
    """
    user = (
        db.query(User).filter(User.email == form.username.strip().lower()).first()
    )
    if user is None or not verify_password(form.password, user.password_hash):
        raise _CREDENTIALS_ERROR

    settings = get_settings()
    token = create_access_token(sub=str(user.id), role=user.role.value)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=(settings.APP_ENV == "prod"),
        path="/",
    )
    logger.info("login ok role=%s", user.role.value)  # không log email/PII
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> UserOut:
    """Thông tin user hiện tại — cần cookie hoặc Bearer header hợp lệ."""
    return UserOut.model_validate(user)

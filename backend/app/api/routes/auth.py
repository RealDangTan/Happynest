"""Authentication routes: login, registration, logout, current identity.

OAuth2 password flow do FastAPI sở hữu; JWT nằm trong cookie httpOnly
SameSite=Lax. All authenticated accounts have the same access.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, get_current_user, get_db
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterIn, TokenOut, UserOut

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
    token = create_access_token(sub=str(user.id))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=(settings.APP_ENV == "prod"),
        path="/",
    )
    logger.info("login ok")  # không log email/PII
    return TokenOut(access_token=token)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> UserOut:
    """Đăng ký tài khoản mới.

    Không set cookie ở đây: FE gọi lại /token ngay sau 201 để vào thẳng app.
    """
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được đăng ký.",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    logger.info("register ok")  # không log email/PII
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Xoá cookie httpOnly — idempotent (JWT stateless, chỉ client bỏ token)."""
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> UserOut:
    """Thông tin user hiện tại — cần cookie hoặc Bearer header hợp lệ."""
    return UserOut.model_validate(user)

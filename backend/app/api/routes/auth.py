"""Authentication routes: login, registration, logout, current identity.

OAuth2 password flow do FastAPI sở hữu; JWT nằm trong cookie httpOnly
SameSite=Lax. All authenticated accounts have the same access.
Google OAuth (2026-10-23): Authorization Code flow qua
`app.services.google_oauth` — account Google-only có `password_hash IS NULL`,
tài khoản password sẵn có được LINK bằng google_sub khi email khớp.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
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
from app.services import google_oauth

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 401 chung — không tiết lộ email có tồn tại hay không (user enumeration).
_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email hoặc mật khẩu không đúng.",
    headers={"WWW-Authenticate": "Bearer"},
)

# 401 riêng cho account Google-only (password_hash NULL): chủ đích KHÁC thông
# điệp chung để user biết phải dùng nút Google — hy sinh một phần user
# enumeration protection đổi lấy UX rõ ràng (decisions.md 2026-10-23).
_GOOGLE_ONLY_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email này đăng nhập bằng Google — hãy dùng nút “Đăng nhập với Google”.",
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
    if user is not None and user.password_hash is None:
        raise _GOOGLE_ONLY_ERROR
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
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        # Phân biệt để user không bối rối: account Google-only không đặt được
        # mật khẩu kiểu này (email tồn tại đã lộ sẵn ở thông điệp riêng của
        # login Google-only — nhất quán).
        if existing.password_hash is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã đăng ký qua Google — hãy đăng nhập bằng nút Google.",
            )
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


def _google_error_redirect(reason: str) -> RedirectResponse:
    """Mọi lỗi flow Google quay về trang login FE kèm `?google_error=<mã>`.

    Redirect RELATIVE (`/login`) để luôn đáp lên origin FE khi đi qua proxy
    same-origin của Next (`next.config.ts` rewrite `/api/*`) — topology chuẩn
    của delivery (cookie httpOnly không cần CORS).
    """
    return RedirectResponse(f"/login?google_error={reason}", status_code=302)


@router.get("/google/login", status_code=status.HTTP_302_FOUND)
def google_login() -> RedirectResponse:
    """Bắt đầu flow: 302 → Google kèm `state` (cookie ngắn hạn chống CSRF).

    Feature flag rỗng (`GOOGLE_CLIENT_ID`/`SECRET`/`REDIRECT_URI`) → 503 rõ
    nguyên nhân thay vì redirect tới Google rồi hỏng lặng lẽ.
    """
    if not google_oauth.google_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Đăng nhập Google chưa được cấu hình trên server — cần "
                "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI "
                "trong backend/.env."
            ),
        )

    state = secrets.token_urlsafe(32)
    settings = get_settings()
    response = RedirectResponse(google_oauth.build_authorization_url(state), status_code=302)
    response.set_cookie(
        key=google_oauth.STATE_COOKIE,
        value=state,
        max_age=google_oauth.STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=(settings.APP_ENV == "prod"),
        path="/api/auth/google",
    )
    logger.info("google oauth start")  # không log state/email
    return response


@router.get("/google/callback", status_code=status.HTTP_302_FOUND)
def google_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Google quay về đây với `?code` → đổi id_token → upsert user → JWT cookie.

    Upsert: khớp `google_sub` trước; nếu chưa có thì khớp email để LINK tài
    khoản password sẵn có; không có cả hai → tạo account mới
    (`password_hash IS NULL`). Thành công → 302 `/` (middleware FE sẽ đưa
    thẳng `/importer` vì cookie đã set).
    """
    expected_state = request.cookies.get(google_oauth.STATE_COOKIE)
    if error or not code:
        logger.info("google oauth denied/error param")
        return _google_error_redirect("denied")
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        logger.warning("google oauth state mismatch")
        return _google_error_redirect("state")

    try:
        id_token = google_oauth.exchange_code(code)
        claims = google_oauth.verify_id_token(id_token)
        identity = google_oauth.extract_identity(claims)
    except Exception:
        logger.warning("google oauth exchange/verify failed", exc_info=True)
        return _google_error_redirect("exchange")

    user = (
        db.query(User).filter(User.google_sub == identity.google_sub).first()
    )
    if user is None:
        user = db.query(User).filter(User.email == identity.email).first()
        if user is not None:
            if user.google_sub is not None:
                # Trùng email nhưng đã gắn sub Google khác — bất thường, không
                # tự ghi đè identity có sẵn.
                logger.warning("google oauth email conflict")
                return _google_error_redirect("email_conflict")
            user.google_sub = identity.google_sub  # link account password sẵn có
        else:
            user = User(
                email=identity.email,
                password_hash=None,
                google_sub=identity.google_sub,
            )
            db.add(user)
    db.commit()

    token = create_access_token(sub=str(user.id))
    settings = get_settings()
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=(settings.APP_ENV == "prod"),
        path="/",
    )
    response.delete_cookie(
        key=google_oauth.STATE_COOKIE, path="/api/auth/google"
    )
    logger.info("google login ok")  # không log email/PII
    return response

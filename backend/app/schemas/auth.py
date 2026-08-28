"""Auth schemas — Phase 04 (docs/plans/04-auth-rbac.md §3.2) + P1.5 register."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole

# RFC-lite: đủ chặn "khong-phai-email" mà không cần thêm dependency email-validator.
_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"


class RegisterIn(BaseModel):
    """P1.5 / FE-08 — đăng ký public, role luôn gán `operations` ở route."""

    email: str = Field(pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    """Trả body cho tiện test/Swagger Bearer — auth thật nằm ở cookie httpOnly."""

    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole

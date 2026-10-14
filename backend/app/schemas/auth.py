"""Authentication schemas; users expose identity only."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


# RFC-lite: đủ chặn "khong-phai-email" mà không cần thêm dependency email-validator.
_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"


class RegisterIn(BaseModel):
    """Public account registration."""

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

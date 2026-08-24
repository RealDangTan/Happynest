"""Auth schemas — Phase 04 (docs/plans/04-auth-rbac.md §3.2)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class TokenOut(BaseModel):
    """Trả body cho tiện test/Swagger Bearer — auth thật nằm ở cookie httpOnly."""

    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole

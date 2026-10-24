"""User identities for login and reviewer attribution."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    # NULL = account Google-only (đăng nhập qua Google OAuth, không có mật
    # khẩu) — migration 0022 nới NOT NULL; login password chặn NULL ở route.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Google identity (`sub` trong id_token) — NULL với account password thuần.
    google_sub: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

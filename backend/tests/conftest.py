"""Shared fixtures — Phase 04 khởi tạo, Phase 11 hoàn thiện chiến lược chung.

Hiện trạng (chấp nhận theo plan): test chạy trên DB Supabase DEV thật qua
internet — chỉ ghi bảng `users` (upsert 2 user seed, vô hại). Chạy cần .env.
"""

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.deps import require_role
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

# Mật khẩu TEST biết trước (khác fallback seed) để test login deterministic.
TEST_PASSWORDS = {
    UserRole.pm: "test-pm-pass-0001",
    UserRole.operations: "test-ops-pass-0002",
}
SEED_EMAILS = {
    UserRole.pm: "pm@thesis.local",
    UserRole.operations: "ops@thesis.local",
}


def _upsert(db, email: str, password_hash: str, role: UserRole) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, password_hash=password_hash, role=role)
        db.add(user)
    else:
        user.password_hash = password_hash
        user.role = role
    return user


@pytest.fixture(scope="session")
def seeded_users():
    """Upsert cả 2 role với mật khẩu test; assert hash argon2 trong DB (DoD 04)."""
    with SessionLocal() as db:
        users = {}
        for role, email in SEED_EMAILS.items():
            h = hash_password(TEST_PASSWORDS[role])
            assert h.startswith("$argon2"), f"hash không phải argon2: {h[:16]}…"
            users[role] = _upsert(db, email, h, role)
        db.commit()

        # Đối chiếu DB thật: prefix $argon2 + role đúng
        for role, email in SEED_EMAILS.items():
            row = db.query(User).filter(User.email == email).one()
            assert row.password_hash.startswith("$argon2")
            assert row.role is role
    return users


@pytest.fixture()
def client(seeded_users):
    """TestClient gắn lifespan; phụ thuộc seeded_users để chắc chắn đã seed."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def pm_guarded_client(client):
    """Mount route guard DEMO pm-only rồi gỡ sau test — chứng minh 403 route-level
    đi qua đúng stack thật (cookie → get_current_user → require_role), không để
    lại endpoint thừa trong production API."""
    routes_before = len(app.routes)
    demo = APIRouter()

    @demo.get("/api/auth/_guard-demo")
    def guard_demo(user: User = Depends(require_role("pm"))):  # noqa: F821
        return {"ok": True}

    app.include_router(demo)
    yield client
    del app.routes[routes_before:]

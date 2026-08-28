"""Shared fixtures — Phase 04 khởi tạo, Phase 11 hoàn thiện chiến lược chung (plan 11 §3.1).

Chiến lược DB trong tests:
- `TEST_DATABASE_URL` env (nếu đặt) GHI ĐÈ `DATABASE_URL` TRƯỚC khi import app —
  dành cho Supabase test project thứ 2 (khuyến nghị plan); không đặt → fallback
  `DATABASE_URL` (DB dev). pydantic-settings ưu tiên env var hơn .env nên ghi đè
  env là đủ để mọi engine bind sang test DB.
- Test có marker `integration` mà DB không kết nối được (mất mạng / project
  pause) → pytest.skip với message rõ — unit thuần vẫn xanh offline.
- KHÔNG truncate/drop schema tự động: DB dev DÙNG CHUNG — mỗi suite tự dọn rác
  theo tiền tố external_ref/id của mình (+ quarantine của phase 09). Auto-wipe
  còn phá luôn `alembic_version`; nếu sau này có test project riêng thì chạy
  `alembic upgrade head` MỘT lần trước khi bật suite integration.
"""

import os

# Phải đứng trước MỌI import app.* dưới đây.
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.api.deps import require_role
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import UserRole
from app.models.product import Product
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


# ------------------------------------------------------------- DB probe (Phase 11)

_db_probe: dict[str, bool] = {"done": False, "ok": False}


def db_reachable() -> bool:
    """SELECT 1 đúng MỘT lần mỗi pytest session (connect_timeout 5s, NullPool,
    engine tạm không đụng pool của app). Kết quả cache cho các test sau."""
    if not _db_probe["done"]:
        engine = create_engine(
            get_settings().database_url_sqla,
            connect_args={"connect_timeout": 5},
            poolclass=NullPool,
        )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _db_probe["ok"] = True
        except Exception:  # OperationalError/DBAPIError bất kỳ → coi như unreachable
            _db_probe["ok"] = False
        finally:
            engine.dispose()
            _db_probe["done"] = True
    return _db_probe["ok"]


_SKIP_MSG = (
    "Supabase not reachable — kiểm tra internet / anti-pause 7 ngày, "
    "hoặc trỏ TEST_DATABASE_URL sang test project đang active"
)


@pytest.fixture(autouse=True)
def integration_needs_real_db(request):
    """Plan 11 §3.1: test integration + DB unreachable → SKIP (không ERROR).

    Autouse function-scoped để chạy TRƯỚC fixture cùng scope mở SessionLocal
    riêng (sim_ids, batch, clean_feedbacks…). Fixture session-scoped cao hơn
    (seeded_users) tự lo phần mình bên trong.
    """
    if request.node.get_closest_marker("integration") is None:
        yield
        return
    if not db_reachable():
        pytest.skip(_SKIP_MSG)
    yield


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
    if not db_reachable():
        pytest.skip(_SKIP_MSG)  # session-scoped chạy TRƯỚC guard function-scoped
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


TEST_PRODUCT_NAME = "voc-test-product"


@pytest.fixture(scope="session")
def test_product():
    """Product dùng chung cho mọi test seed feedback (plan 21: product_id NOT
    NULL). Idempotent — test suite rerun không nhân bản; KHÔNG xoá khi teardown
    (row 1 row vô hại, tránh race giữa các suite song song)."""
    if not db_reachable():
        pytest.skip(_SKIP_MSG)
    with SessionLocal() as db:
        product = db.query(Product).filter(Product.name == TEST_PRODUCT_NAME).first()
        if product is None:
            product = Product(
                name=TEST_PRODUCT_NAME,
                description="Product fixture cho test suite (plan 21).",
            )
            db.add(product)
            db.commit()
            db.refresh(product)
        return product


@pytest.fixture()
def db_session():
    """Session function-scoped, ROLLBACK khi test xong (plan 11 §3.1).

    Đảm bảo những gì test INSERT qua fixture này không bám lại DB; row do code
    khác COMMIT trong test (ingest API…) phải dọn bằng prefix/id như hiện nay.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


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

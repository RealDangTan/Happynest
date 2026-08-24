"""Seed 2 user mặc định — Phase 04 (docs/plans/04-auth-rbac.md §3.5).

Idempotent (upsert theo email):
- pm@thesis.local   role pm
- ops@thesis.local  role operations

Mật khẩu đọc env SEED_PM_PASSWORD / SEED_OPS_PASSWORD; thiếu → fallback dev
mặc định và IN CẢNH BÁO ĐỔI NGAY.

Chạy: `uv run python scripts/seed_users.py` (từ thư mục backend/).
"""

import os
import sys
from pathlib import Path

# Chạy trực tiếp `uv run python scripts/seed_users.py`: thêm backend/ vào path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User

DEFAULT_PM_PASSWORD = "pm-dev-password"
DEFAULT_OPS_PASSWORD = "ops-dev-password"

SEED_USERS = [
    ("pm@thesis.local", "SEED_PM_PASSWORD", DEFAULT_PM_PASSWORD, UserRole.pm),
    ("ops@thesis.local", "SEED_OPS_PASSWORD", DEFAULT_OPS_PASSWORD, UserRole.operations),
]


def upsert_user(db, email: str, password_hash: str, role: UserRole) -> bool:
    """True = tạo mới, False = cập nhật user đã có."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        db.add(User(email=email, password_hash=password_hash, role=role))
        return True
    user.password_hash = password_hash
    user.role = role
    return False


def main() -> int:
    get_settings()  # fail fast nếu .env thiếu DATABASE_URL
    configure_logging()

    used_fallback = False
    with SessionLocal() as db:
        for email, env_var, fallback_password, role in SEED_USERS:
            password = os.environ.get(env_var)
            if not password:
                password = fallback_password
                used_fallback = True
                print(
                    f"⚠️  [{email}] chưa đặt {env_var} — dùng mật khẩu dev mặc định. "
                    f"ĐỔI NGAY bằng cách chạy lại với biến môi trường này."
                )
                # Không in mật khẩu ra log — chỉ in tên biến.
            created = upsert_user(db, email, hash_password(password), role)
            print(f"{'tạo mới' if created else 'cập nhật'}: {email} (role={role.value})")
        db.commit()
        print("Seed hoàn tất.")

    if used_fallback:
        print("⚠️  CẢNH BÁO: có user dùng mật khẩu fallback — đặt SEED_PM_PASSWORD / "
              "SEED_OPS_PASSWORD rồi chạy lại để đổi ngay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

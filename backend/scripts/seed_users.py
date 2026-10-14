"""Seed two demo accounts with identical access (idempotent email upsert).

Legacy seed email/password environment names remain compatible.
Run: uv run python scripts/seed_users.py
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
from app.models.user import User

DEFAULT_PM_PASSWORD = "pm-dev-password"
DEFAULT_OPS_PASSWORD = "ops-dev-password"

SEED_USERS = [
    ("pm@thesis.local", "SEED_PM_PASSWORD", DEFAULT_PM_PASSWORD),
    ("ops@thesis.local", "SEED_OPS_PASSWORD", DEFAULT_OPS_PASSWORD),
]


def upsert_user(db, email: str, password_hash: str) -> bool:
    """True = tạo mới, False = cập nhật user đã có."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        db.add(User(email=email, password_hash=password_hash))
        return True
    user.password_hash = password_hash
    return False


def main() -> int:
    get_settings()  # fail fast nếu .env thiếu DATABASE_URL
    configure_logging()

    used_fallback = False
    with SessionLocal() as db:
        for email, env_var, fallback_password in SEED_USERS:
            password = os.environ.get(env_var)
            if not password:
                password = fallback_password
                used_fallback = True
                print(
                    f"⚠️  [{email}] chưa đặt {env_var} — dùng mật khẩu dev mặc định. "
                    f"ĐỔI NGAY bằng cách chạy lại với biến môi trường này."
                )
                # Không in mật khẩu ra log — chỉ in tên biến.
            created = upsert_user(db, email, hash_password(password))
            print(f"{'tạo mới' if created else 'cập nhật'}: {email}")
        db.commit()
        print("Seed hoàn tất.")

    if used_fallback:
        print("⚠️  CẢNH BÁO: có user dùng mật khẩu fallback — đặt SEED_PM_PASSWORD / "
              "SEED_OPS_PASSWORD rồi chạy lại để đổi ngay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

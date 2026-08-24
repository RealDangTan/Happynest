"""Dependencies dùng chung cho routes.

⚠️ SCAFFOLD PHASE 08: phase 08 chạy trước 04/05 nên deps.py mới chỉ có get_db.
Phase 04 (docs/plans/04-auth-rbac.md) sẽ MỞ RỘNG — không viết lại — với
`get_current_user`, `require_role`.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: 1 session per request, đóng chắc chắn sau response."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

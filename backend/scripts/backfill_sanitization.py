"""Backfill sanitization cho row cũ — Phase 06 (06-pii-presidio-service.md §3.2).

Quét các row có `sanitized_content IS NULL` (nhập trước khi wiring Phase 06),
sanitize từng row và COMMIT TỪNG ROW — crash giữa chừng không mất tiến độ.

Chạy: uv run python scripts/backfill_sanitization.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.feedback import Feedback  # noqa: E402
from app.services.presidio_service import init_presidio, mode, sanitize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill sanitized_content cho row cũ.")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đếm, không ghi.")
    args = parser.parse_args()

    init_presidio()
    print("Chế độ presidio:", mode()["mode"])
    with SessionLocal() as db:
        pending_ids = db.scalars(
            select(Feedback.id).where(Feedback.sanitized_content.is_(None))
        ).all()
        total = len(pending_ids)
        print(f"Cần backfill: {total} row")
        if args.dry_run or total == 0:
            return 0

        done = pii_hits = 0
        # Nạp lại từng row theo id để commit từng cái, session ngắn cho mỗi lần.
        for fid in pending_ids:
            with SessionLocal() as row_session:
                row = row_session.get(Feedback, fid)
                if row is None:  # đã bị xóa giữa chừng
                    continue
                result = sanitize(row.raw_content)
                row.sanitized_content = result.sanitized_text
                row.pii_detected = result.pii_detected
                row.pii_entities = [e.model_dump() for e in result.entities]
                row_session.commit()
            done += 1
            pii_hits += int(result.pii_detected)
            if done % 50 == 0:
                print(f"  … {done}/{total}")

    print(f"✅ Đã sanitize {done}/{total} row ({pii_hits} row có PII).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

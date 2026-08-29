"""CLI chạy closed-loop impact check (plan 27 Task 2 — điền gap "no trigger"
của phase 20): đo volume feedback trước/sau cho action accepted/edited đã đủ
window tuổi. Idempotent per action.

Chạy: uv run python scripts/run_impact_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.impact_service import run_impact_checks  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        results = run_impact_checks(db)
    if not results:
        print("Không có action nào đủ tuổi window cần đo.")
        return 0
    for r in results:
        print(
            f"action {r['action_id']}: before={r['before_count']} "
            f"after={r['after_count']} delta={r['delta_ratio']}"
        )
    print(f"Đã đo {len(results)} impact check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

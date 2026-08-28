"""CLI import CSV feedback — Phase 05 (05-feedback-ingestion.md §3.4).

Chạy: uv run python scripts/import_csv.py path/to/file.csv
Tự dựng session từ .env, KHÔNG cần app đang chạy. Gọi đúng service layer
`import_csv_rows` để API và CLI không lệch logic.
"""

import argparse
import sys
from pathlib import Path

# Cho phép chạy trực tiếp `python scripts/import_csv.py` mà không cần cài package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.ingest_service import (  # noqa: E402
    get_default_product,
    import_csv_rows,
    iter_csv_dicts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import feedback từ file CSV.")
    parser.add_argument("csv_path", type=Path, help="Đường dẫn file CSV (UTF-8, có BOM hay không đều được).")
    args = parser.parse_args()

    if not args.csv_path.is_file():
        print(f"❌ Không tìm thấy file: {args.csv_path}")
        return 2

    with args.csv_path.open("rb") as f, SessionLocal() as session:
        product = get_default_product(session)
        report = import_csv_rows(session, iter_csv_dicts(f), product_id=product.id)

    print(f"✅ Imported: {report.imported}")
    print(f"⚠️  Failed:   {report.failed}")
    for err in report.errors:
        print(f"   - dòng {err.row}: {err.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

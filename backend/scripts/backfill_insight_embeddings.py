"""Backfill embedding cho insights cũ (phase 18 Task 5 Step 5.1).

Idempotent — chạy lại bỏ qua row đã có vector. Text nhúng = f"{title}. {summary}"
(title/summary là dữ liệu tổng hợp đã qua biên PII ở tầng insight).

Usage:
    uv run python scripts/backfill_insight_embeddings.py [--limit N]

Env: INSIGHT_EMBED_BACKFILL_LIMIT (default 200) — trần mỗi lượt chạy để không
đốt quota embeddings vô hạn.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import APIError  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.insight import Insight  # noqa: E402
from app.services.embedder import EmbeddingDimError, embed_one, store_embedding  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Ghi đè INSIGHT_EMBED_BACKFILL_LIMIT (default env hoặc 200)",
    )
    args = parser.parse_args()

    limit = args.limit if args.limit is not None else int(
        os.environ.get("INSIGHT_EMBED_BACKFILL_LIMIT", "200")
    )

    with SessionLocal() as db:
        rows = db.scalars(
            select(Insight)
            .where(Insight.embedding.is_(None))
            .order_by(Insight.created_at.desc())
            .limit(limit)
        ).all()
        print(f"insights chưa có embedding: {len(rows)} (limit {limit})")

        done = failed = 0
        for ins in rows:
            try:
                # idempotent: kiểm tra lại trong transaction (row có thể được
                # fill bởi tiến trình khác giữa lúc SELECT và lượt này)
                db.refresh(ins)
                if ins.embedding is not None:
                    continue
                store_embedding(db, ins, embed_one(f"{ins.title}. {ins.summary}"))
                db.commit()
                done += 1
            except (EmbeddingDimError, APIError) as exc:
                db.rollback()
                failed += 1
                print(f"  FAIL {str(ins.id)[:8]}: {type(exc).__name__}: {exc}")

        print(f"backfill xong: embedded={done} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

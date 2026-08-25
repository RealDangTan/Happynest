"""Evidence blocker rule §5 (Phase 14) — sweep CLUSTER_MIN_SIZE trên data thật.

Plan 14 §5: HDBSCAN ra 0–1 cụm hoặc noise >50% trên data thật → thử sweep
`CLUSTER_MIN_SIZE` {5, 8, 10, 15} trong 1 script evidence; vẫn tệ → STOP +
entry decisions (kèm JSON kết quả) + fallback similarity threshold.

Đọc embedding THẬT từ Supabase dev (không seed thêm), chạy HDBSCAN
metric=cosine cho từng giá trị min_cluster_size, in JSON kết quả ra stdout
và ghi `docs/evidence/cluster-sweep-results.json`.

Chạy:  uv run python scripts/evidence_cluster_sweep.py
Yêu cầu: Supabase reachable. KHÔNG in nội dung feedback (PII boundary).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.feedback import Feedback  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        rows = db.execute(select(Feedback)).scalars().all()
    X = np.stack(
        [
            np.asarray(fb.embedding, dtype=np.float32)
            for fb in rows
            if fb.embedding is not None
        ]
    )
    print(f"embedded rows: {len(X)} dim={X.shape[1] if len(X) else '-'}")

    from sklearn.cluster import HDBSCAN

    results = []
    for min_size in (5, 8, 10, 15):
        t0 = time.perf_counter()
        labels = HDBSCAN(metric="cosine", min_cluster_size=min_size).fit_predict(X)
        elapsed = round(time.perf_counter() - t0, 3)
        sizes: dict[int, int] = {}
        for lb in labels:
            if lb != -1:
                sizes[int(lb)] = sizes.get(int(lb), 0) + 1
        noise = int((labels == -1).sum())
        entry = {
            "min_cluster_size": min_size,
            "n_clusters": len(sizes),
            "cluster_sizes": sorted(sizes.values(), reverse=True),
            "noise": noise,
            "noise_ratio": round(noise / len(labels), 3),
            "fit_seconds": elapsed,
        }
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False))

    out = Path(__file__).resolve().parents[2] / "docs" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "cluster-sweep-results.json"
    dest.write_text(
        json.dumps({"n_rows": len(X), "metric": "cosine", "sweeps": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved → {dest}")


if __name__ == "__main__":
    main()

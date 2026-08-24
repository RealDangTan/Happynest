"""Spike S4 — sklearn HDBSCAN metric cosine có sane trên toy vectors?

Chuẩn bị cho phase clustering (chưa viết production code ở giai đoạn này):
1. Sinh 200 vector 1536-d giả: 3 cụm (center random cố định seed=42 + noise nhỏ
   quanh center) + đúng 20 điểm noise đều -> ground truth để đối chiếu.
2. HDBSCAN(metric="cosine") sweep min_cluster_size {5,10,15}:
   in số cluster tìm được + % noise mỗi cấu hình.
3. Đo thời gian fit từng cấu hình + tổng (pass criterion: tổng <5s).

Pass: <5s, noise fraction hợp lý (không 0%, không >50% khi dữ liệu có cụm rõ),
cluster count ≈ 3 ở min_cluster_size vừa.

Dependency scikit-learn KHÔNG nằm trong pin §1 — chạy ad-hoc spike-only:
    uv run --with scikit-learn python ../scripts/spikes/s4_hdbscan_toy.py
Output JSON ra stdout + results/ (gitignored). Không đụng DB, không LLM tokens.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

utf8_needed = sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8"
if utf8_needed:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import save_result  # noqa: E402

N_DIMS = 1536
N_CLUSTERS_TRUE = 3
N_PER_CLUSTER = 60
N_NOISE = 20  # 60*3 + 20 = 200
SEED = 42
MIN_CLUSTER_SIZES = [5, 10, 15]


def make_toy(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Trả (X[200,1536], labels_true) — cụm = center + gaussian nhỏ; noise uniform."""
    centers = rng.uniform(0.0, 1.0, size=(N_CLUSTERS_TRUE, N_DIMS))
    xs, ys = [], []
    for ci, center in enumerate(centers):
        pts = center + rng.normal(0.0, 0.02, size=(N_PER_CLUSTER, N_DIMS))
        xs.append(pts)
        ys.append(np.full(N_PER_CLUSTER, ci))
    xs.append(rng.uniform(0.0, 1.0, size=(N_NOISE, N_DIMS)))
    ys.append(np.full(N_NOISE, -1))
    X = np.vstack(xs)
    y = np.concatenate(ys)
    perm = rng.permutation(X.shape[0])
    return X[perm], y[perm]


def main() -> None:
    from sklearn import __version__ as sklearn_version
    from sklearn.cluster import HDBSCAN

    rng = np.random.default_rng(SEED)
    report: dict = {
        "spike": "S4",
        "seed": SEED,
        "n_points": N_CLUSTERS_TRUE * N_PER_CLUSTER + N_NOISE,
        "n_dims": N_DIMS,
        "true_clusters": N_CLUSTERS_TRUE,
        "true_noise": N_NOISE,
        "metric": "cosine",
        "sklearn_version": sklearn_version,
        "configs": [],
    }

    t_start = time.perf_counter()
    X, _ = make_toy(rng)
    report["toy_build_seconds"] = round(time.perf_counter() - t_start, 4)

    for mcs in MIN_CLUSTER_SIZES:
        t0 = time.perf_counter()
        labels = HDBSCAN(metric="cosine", min_cluster_size=mcs).fit_predict(X)
        fit_s = time.perf_counter() - t0
        n_noise = int((labels == -1).sum())
        cfg = {
            "min_cluster_size": mcs,
            "n_clusters": len(set(labels)) - (1 if n_noise else 0),
            "noise_pct": round(100.0 * n_noise / X.shape[0], 1),
            "fit_seconds": round(fit_s, 3),
        }
        report["configs"].append(cfg)

    total_s = time.perf_counter() - t_start
    report["total_seconds"] = round(total_s, 3)

    # Pass: nhanh + tồn tại cấu hình "vừa" cho ≈3 cụm với noise fraction hợp lý.
    sane_cfgs = [
        c for c in report["configs"] if c["n_clusters"] == 3 and 0 < c["noise_pct"] < 50
    ]
    report["sane_config_min_cluster_sizes"] = [c["min_cluster_size"] for c in sane_cfgs]
    report["pass"] = bool(total_s < 5.0 and sane_cfgs)

    save_result("s4_hdbscan_toy", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

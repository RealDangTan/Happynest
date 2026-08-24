"""Spike S3 — Embeddings API + roundtrip pgvector qua Supabase?

1. Call /v1/embeddings cho 10 câu VI -> in model server report + số chiều thực tế,
   đối chiếu EMBEDDING_DIM(ENSIONS). Lệch vẫn chạy hết với dims thực đo để lấy bằng chứng,
   nhưng flag dim_mismatch=true để ghi Decision Log (đổi VECTOR(n)).
2. CREATE TABLE toy public._spike_vec(v vector(N)) qua psycopg thuần (session pooler).
3. Insert 10 vector; mỗi câu query cosine top-3 -> self-match phải rank #1, sim ~ 1.0;
   đo latency từng query (WAN ~100ms bình thường).
Drop bảng toy trong finally. Output JSON ra stdout + results/ (gitignored).
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import db_params, embedding_cfg, load_env_file, save_result, utf8_stdio  # noqa: E402

utf8_stdio()

from openai import OpenAI  # noqa: E402
import psycopg  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

SENTENCES = [
    "Ứng dụng hay bị crash khi tôi mở camera quét mã QR.",
    "Giao diện trang quản trị khó nhìn, chữ quá nhỏ.",
    "Tôi rất hài lòng với tốc độ phản hồi của chatbot hỗ trợ.",
    "Thanh toán qua ví điện tử đôi khi bị treo ở bước xác nhận.",
    "Tính năng thông báo đẩy hoạt động tốt trên Android nhưng lỗi trên iOS.",
    "Bản cập nhật mới làm ứng dụng nặng máy, pin tụt nhanh.",
    "Chức năng tìm kiếm trả về kết quả không liên quan gì đến từ khóa.",
    "Đồng bộ dữ liệu giữa điện thoại và web mượt mà, chính xác.",
    "Màn hình đăng nhập bị trượt khi bàn phím hiện lên.",
    "Nhóm phát triển phản hồi yêu cầu tính năng nhanh và nhiệt tình.",
]

TABLE = "public._spike_vec"


def main():
    env = load_env_file()
    cfg = embedding_cfg(env)
    client = OpenAI(
        base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=120, max_retries=1
    )
    report = {
        "spike": "S3",
        "embedding_model_requested": cfg["model"],
        "contract_dims": cfg["contract_dims"],
        "db_host_suffix": ".".join(db_params(env)["host"].split(".")[-4:]),
        "db_port": db_params(env)["port"],
    }

    resp = client.embeddings.create(model=cfg["model"], input=SENTENCES)
    ordered = sorted(resp.data, key=lambda d: d.index)
    vectors = [np.asarray(d.embedding, dtype=np.float32) for d in ordered]
    measured_dims = int(vectors[0].shape[0])
    report["embedding_model_reported"] = resp.model
    report["measured_dims"] = measured_dims
    report["dim_mismatch_vs_contract"] = measured_dims != cfg["contract_dims"]
    if report["dim_mismatch_vs_contract"]:
        report["dim_note"] = (
            "LECH hop dong — can entry Decision Log doi EMBEDDING_DIM + VECTOR(n)"
        )

    conn = psycopg.connect(
        **db_params(env),
        options="-c search_path=extensions,public",
        connect_timeout=20,
    )
    insert_ok = False
    latencies_ms = []
    sims = []
    rank_ok = []
    try:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE {TABLE} (id serial PRIMARY KEY, v vector({measured_dims}))")
            ids = []
            for vec in vectors:
                cur.execute(f"INSERT INTO {TABLE}(v) VALUES (%s) RETURNING id", (vec,))
                ids.append(cur.fetchone()[0])
            conn.commit()
            insert_ok = True

            for i, vec in enumerate(vectors):
                t0 = time.perf_counter()
                cur.execute(
                    f"SELECT id, v <=> %s AS dist FROM {TABLE} ORDER BY dist LIMIT 3",
                    (vec,),
                )
                rows = cur.fetchall()
                latencies_ms.append(round((time.perf_counter() - t0) * 1000, 1))
                top_id, top_dist = rows[0]
                rank_ok.append(top_id == ids[i])
                sims.append(round(1 - float(top_dist), 4))
            conn.commit()
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
            conn.commit()
        except Exception:
            conn.rollback()
        conn.close()

    report.update(
        {
            "insert_ok": insert_ok,
            "all_self_match_rank_1": all(rank_ok),
            "self_similarity_min": min(sims) if sims else None,
            "latency_ms_avg": round(sum(latencies_ms) / len(latencies_ms), 1) if latencies_ms else None,
            "latency_ms_max": max(latencies_ms) if latencies_ms else None,
            "toy_table_dropped": True,
        }
    )
    report["pass"] = bool(
        insert_ok and report["all_self_match_rank_1"] and not report["dim_mismatch_vs_contract"]
    )
    save_result("s3_embedding_pgvector", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

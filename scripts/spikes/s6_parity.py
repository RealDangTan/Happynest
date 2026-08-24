"""Spike S6 (PHẦN KHẢ DỤNG NGAY phase 02) — Parity Windows-native <-> Supabase.

Theo plan §3.4: S6 đầy đủ cần migrations Phase 03 (Alembic upgrade head + ORM insert/query).
Phần chạy ngay hôm nay: (1) PG reachable qua session pooler từ Windows; (2) raw psycopg
roundtrip (CREATE/INSERT/SELECT/DROP); (3) baseline latency WAN 20 query tuần tự.
Phần Alembic/ORM sẽ hoàn tất ngay sau Phase 03 — ghi rõ trong decisions.md ngày chạy từng phần.
Output JSON ra stdout + results/s6_parity_result.json (gitignored).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import db_params, load_env_file, save_result, utf8_stdio  # noqa: E402

utf8_stdio()

import psycopg  # noqa: E402


def main():
    env = load_env_file()
    params = db_params(env)
    report = {
        "spike": "S6",
        "scope": "partial_pre_phase03",
        "deferred_part": "alembic_upgrade_head + ORM feedbacks insert/query (ngay sau Phase 03)",
        "db_host_suffix": ".".join(params["host"].split(".")[-4:]),
        "db_port": params["port"],
    }
    conn = psycopg.connect(
        **params, options="-c search_path=extensions,public", connect_timeout=20
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version_full = cur.fetchone()[0]
            report["server_version_short"] = " ".join(version_full.split()[:2])

            # raw roundtrip bảng toy riêng của S6 (không đụng bảng S3)
            cur.execute(
                "CREATE TABLE public._spike_parity (id integer PRIMARY KEY, note text)"
            )
            cur.execute(
                "INSERT INTO public._spike_parity (id, note) VALUES (%s, %s)",
                (1, "roundtrip-check"),
            )
            cur.execute("SELECT note FROM public._spike_parity WHERE id = %s", (1,))
            fetched = cur.fetchone()[0]
            conn.commit()
            report["roundtrip_ok"] = fetched == "roundtrip-check"

            timings = []
            for _ in range(20):
                t0 = time.perf_counter()
                cur.execute("SELECT 1")
                cur.fetchall()
                timings.append((time.perf_counter() - t0) * 1000)
            conn.commit()
            timings.sort()
            report["trivial_query_latency_ms"] = {
                "avg": round(sum(timings) / len(timings), 1),
                "min": round(timings[0], 1),
                "max": round(timings[-1], 1),
                "n_sequential": 20,
            }

            cur.execute("DROP TABLE IF EXISTS public._spike_parity")
            conn.commit()
            report["toy_table_dropped"] = True
    finally:
        conn.close()

    report["partial_pass"] = bool(report.get("roundtrip_ok"))
    save_result("s6_parity", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Debug script — bắn N request THẬT (LLM thật) qua HTTP API đúng như web.

Usage (từ backend/):
    uv run python scripts/debug_real_llm_runs.py                 # 5 runs, product mặc định
    uv run python scripts/debug_real_llm_runs.py --runs 2 --product-id <uuid>
    uv run python scripts/debug_real_llm_runs.py --list-stuck    # xem run kẹt
    uv run python scripts/debug_real_llm_runs.py --mark-stuck-failed  # dọn run kẹt

Yêu cầu: uvicorn đang chạy (mặc định http://127.0.0.1:8000) + LLM keys trong .env.
"""

import argparse
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.analysis_run import AnalysisRun  # noqa: E402
from app.models.enums import RunStatus  # noqa: E402

DEFAULT_PRODUCT_ID = "13954833-f8b5-472f-a0d3-b9ad677323b5"  # Happynest

QUESTIONS = [
    "Why did accuracy complaints rise recently?",
    "Điều gì khiến người dùng phàn nàn nhiều nhất tuần này?",
    "Which problem hurts users the most right now?",
    "Tóm tắt các lỗi hồi quy (regression) người dùng đang gặp",
    "Are there any safety or privacy concerns in the feedback?",
]


def login(client: httpx.Client, base_url: str) -> None:
    password = os.environ.get("SEED_PM_PASSWORD", "pm-dev-password")
    resp = client.post(
        f"{base_url}/api/auth/token",
        data={"username": "pm@thesis.local", "password": password},
    )
    if resp.status_code != 200:
        raise SystemExit(f"login failed: {resp.status_code} {resp.text[:300]}")
    print("login ok (pm@thesis.local)")


def list_stuck() -> None:
    with SessionLocal() as s:
        rows = (
            s.query(AnalysisRun)
            .filter(AnalysisRun.status == RunStatus.running)
            .order_by(AnalysisRun.started_at.desc())
            .all()
        )
        if not rows:
            print("không có run kẹt.")
            return
        for r in rows:
            age = datetime.now(timezone.utc) - r.started_at
            print(f"{r.id}  running  age={age}  started={r.started_at}")


def mark_stuck_failed(min_age_hours: float) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as s:
        rows = (
            s.query(AnalysisRun)
            .filter(AnalysisRun.status == RunStatus.running)
            .all()
        )
        changed = 0
        for r in rows:
            age_h = (now - r.started_at).total_seconds() / 3600
            if age_h >= min_age_hours:
                r.status = RunStatus.failed
                r.error = "marked failed by debug script (stuck running)"
                r.completed_at = now
                changed += 1
                print(f"marked failed: {r.id} (age {age_h:.1f}h)")
        s.commit()
        print(f"đã đánh dấu {changed} run failed.")
        return changed


def fire_and_trace(client: httpx.Client, base_url: str, product_id: str,
                   question: str, poll_sec: int, timeout_sec: int) -> None:
    print(f"\n--- {question}")
    resp = client.post(
        f"{base_url}/api/agent/runs",
        json={"product_id": product_id, "question": question},
    )
    if resp.status_code != 200:
        print(f"  POST /api/agent/runs FAIL: {resp.status_code} {resp.text[:300]}")
        return
    run_id = resp.json()["run_id"]
    print(f"  run_id={run_id}")

    deadline = time.monotonic() + timeout_sec
    last_status = None
    while time.monotonic() < deadline:
        try:
            r = client.get(f"{base_url}/api/agent/runs/{run_id}")
        except httpx.HTTPError as exc:
            print(f"  poll network error ({type(exc).__name__}) — retry")
            time.sleep(poll_sec)
            continue
        if r.status_code != 200:
            print(f"  GET status FAIL: {r.status_code} {r.text[:200]}")
            return
        data = r.json()
        status = data.get("status")
        prog = data.get("progress")
        prog_sig = (prog or {}).get("iteration"), (prog or {}).get("last_tool")
        if status != last_status or (prog_sig != getattr(fire_and_trace, "_last_prog", None)
                                     and status == "running"):
            print(f"  [{time.strftime('%H:%M:%S')}] status={status} "
                  f"error={data.get('error')} progress={prog}")
            last_status = status
            fire_and_trace._last_prog = prog_sig
        pending = data.get("pending_approval")
        if status == "failed":
            print(f"  => FAILED: {data.get('error')}")
            return
        if pending:
            insight = (pending or {}).get("insight") or {}
            evidence = (pending or {}).get("evidence") or []
            print(f"  => GATE #2 (pending_approval): title={insight.get('title')!r} "
                  f"evidence={len(evidence)}")
            return
        time.sleep(poll_sec)
    print(f"  => TIMEOUT sau {timeout_sec}s — run có thể bị kẹt ở '{last_status}'")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--poll-sec", type=int, default=5)
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--list-stuck", action="store_true")
    parser.add_argument("--mark-stuck-failed", action="store_true")
    parser.add_argument("--min-age-hours", type=float, default=1.0)
    args = parser.parse_args()

    get_settings()

    if args.list_stuck:
        list_stuck()
        return 0
    if args.mark_stuck_failed:
        mark_stuck_failed(args.min_age_hours)
        return 0

    with httpx.Client(timeout=30) as client:
        login(client, args.base_url)
        for q in QUESTIONS[: args.runs]:
            fire_and_trace(client, args.base_url, args.product_id, q,
                           args.poll_sec, args.timeout_sec)
    return 0


if __name__ == "__main__":
    sys.exit(main())

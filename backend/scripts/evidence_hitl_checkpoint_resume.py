"""Bằng chứng luận văn #1 (Phase 13) — HITL checkpoint SỐNG SÓT restart process.

Tự động hóa thủ tục docs/evidence/hitl-checkpoint-resume.md trên API production
thật (uvicorn thật, KHÔNG TestClient):

    Bước 1  seed 1 feedback pending → start server (port riêng, mặc định 8010)
    Bước 2  POST /reviews reject → đợi thread xuất hiện trong `checkpoints`
            rồi KILL cứng process (giữa interrupt và resume)
    Bước 3  đối chiếu SQL: thread tồn tại, human_reviews còn TRỐNG
    Bước 4  start process MỚI → POST ĐÚNG body cũ → kỳ vọng 200 `rejected`,
            human_reviews/correction_examples ĐÚNG 1 dòng mỗi bảng
    Bước 5  POST lần 3 → 409; dọn dẹp toàn bộ row + checkpoint

Chạy:  uv run python scripts/evidence_hitl_checkpoint_resume.py
Yêu cầu: Supabase reachable. KHÔNG log nội dung feedback (PII boundary).
"""

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Chạy trực tiếp `uv run python scripts/…`: thêm backend/ vào path (y hệt seed_users.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8010
BASE = f"http://127.0.0.1:{PORT}"
PM_EMAIL, PM_PASSWORD = "pm@thesis.local", "test-pm-pass-0001"

from sqlalchemy import text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import ReviewStatus, Sentiment, Severity  # noqa: E402
from app.models.feedback import Feedback  # noqa: E402


def _sql(query: str, **params):
    with SessionLocal() as db:
        return db.execute(text(query), params).all()


def _http(method: str, path: str, body: dict | None = None, token: str | None = None,
          timeout: float = 300):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def _start_server(log_path: str) -> subprocess.Popen:
    log = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        stdout=log, stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 180  # Stanza boot nặng ~30-90s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/api/health", timeout=3) as r:
                if r.status == 200:
                    return proc
        except Exception:
            time.sleep(2)
    proc.kill()
    raise RuntimeError("server không boot nổi trong 180s — xem " + log_path)


def main() -> None:
    body = {"action": "reject", "reason": "spam (evidence tự động)"}

    # ---- Bước 1: seed pending -------------------------------------------------
    # KHÔNG tự đặt id — để DB sinh rồi ĐỌC LẠI sau commit (refresh) làm fid;
    # tự sinh fid riêng mà không gán vào row là lỗi 404 kinh điển.
    with SessionLocal() as db:
        fb = Feedback(
            source="hitl-evidence",
            external_ref=f"hitl-evidence-{uuid.uuid4().hex[:8]}",
            raw_content="[evidence] nội dung test — không PII",
            sanitized_content="[evidence] app crash khi tải file đính kèm",
            created_at=datetime.now(timezone.utc),
            categories=["lỗi kỹ thuật"], ai_issue=None,
            sentiment=Sentiment.negative, severity=Severity.high,
            confidence=0.55, requires_human_review=True,
            review_status=ReviewStatus.pending,
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        fid = fb.id
    tid = f"hitl-{fid}"
    print(f"Bước 1: seeded pending ✓\nfeedback_id = {fid}\nthread_id   = {tid}")

    # ---- Bước 2: server #1 → POST reject → kill giữa interrupt/resume --------
    proc = _start_server("evidence-server-1.log")
    # login dùng form-urlencoded (OAuth2PasswordRequestForm)
    req = urllib.request.Request(
        BASE + "/api/auth/token",
        data=urllib.parse.urlencode(
            {"username": PM_EMAIL, "password": PM_PASSWORD}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        token = json.loads(r.read())["access_token"]
    print("Bước 2a: login ✓")

    result: dict = {}

    def fire():
        result["resp"] = _http("POST", f"/api/reviews/{fid}", body, token)

    threading.Thread(target=fire, daemon=True).start()

    # Cửa sổ crash ĐẮT GIÁ nhất: apply_action đã commit review_status (row rời
    # 'pending') nhưng record_correction CHƯA kịp commit dòng log — giữa hai
    # commits này graph phải ghi checkpoint qua WAN (~9s) nên cửa sổ rộng.
    # Crash ở đây mô phỏng đúng loại mất mát mà idempotency marker sinh ra để
    # cứu: restart + retry cùng body PHẢI chạy nốt phần thiếu (self-heal).
    deadline = time.time() + 300
    while time.time() < deadline:
        if "resp" in result:
            break  # request đã kết thúc (bất kể mã) — hết cửa sổ, xử lý bên dưới
        st = _sql(
            "SELECT review_status::text FROM feedbacks WHERE id = CAST(:f AS uuid)",
            f=str(fid),
        )[0][0]
        n_log = _sql(
            "SELECT count(*) FROM human_reviews WHERE feedback_id = CAST(:f AS uuid)",
            f=str(fid),
        )[0][0]
        if st != "pending" and n_log == 0:
            break  # ĐANG ở giữa cửa sổ → kill ngay
        time.sleep(0.2)
    proc.kill()
    proc.wait(timeout=30)
    print("Bước 2b: KILL CỨNG process #1 (TerminateProcess)")

    # ---- Bước 3: đối chiếu state trên Postgres --------------------------------
    st = _sql(
        "SELECT review_status::text FROM feedbacks WHERE id = CAST(:f AS uuid)",
        f=str(fid),
    )[0][0]
    n_review = _sql(
        "SELECT count(*) FROM human_reviews WHERE feedback_id = CAST(:f AS uuid)",
        f=str(fid))[0][0]
    n_ckpt = _sql(
        "SELECT count(*) FROM checkpoints WHERE thread_id = :t", t=tid)[0][0]
    assert n_ckpt >= 1, "checkpoint phải tồn tại sau kill"
    assert st != "pending", "review_status phải đã rời pending (apply_action đã commit)"
    assert n_review == 0, (
        f"kịch bản yêu cầu crash TRƯỚC khi dòng log kịp commit — thấy {n_review} dòng; "
        "chạy lại để bắt đúng cửa sổ"
    )
    print(f"Bước 3: checkpoints={n_ckpt}, review_status='{st}', human_reviews=0 ✓ "
          "(trạng thái đã commit nhưng THIẾU dòng log — crash đúng cửa sổ)")

    # ---- Bước 4: process MỚI resume cùng body ---------------------------------
    proc2 = _start_server("evidence-server-2.log")
    try:
        status, payload = _http("POST", f"/api/reviews/{fid}", body, token)
        print(f"Bước 4: POST lại cùng body → HTTP {status}")
        assert status == 200, f"kỳ vọng 200, nhận {status}: {payload}"
        assert payload["review_status"] == "rejected", payload["review_status"]
        n_rev = _sql("SELECT count(*) FROM human_reviews WHERE "
                     "feedback_id = CAST(:f AS uuid)", f=str(fid))[0][0]
        n_ex = _sql("SELECT count(*) FROM correction_examples WHERE "
                    "feedback_id = CAST(:f AS uuid)", f=str(fid))[0][0]
        assert n_rev == 1 and n_ex == 1, f"phải ĐÚNG 1 dòng mỗi bảng ({n_rev},{n_ex})"
        print(f"Bước 4b: human_reviews={n_rev}, correction_examples={n_ex} ✓ "
              "(không nhân bản dù graph từng chạy dở)")

        # ---- Bước 5: POST lần 3 → 409, dọn dẹp --------------------------------
        status3, _ = _http("POST", f"/api/reviews/{fid}", body, token)
        assert status3 == 409, f"lần 3 kỳ vọng 409, nhận {status3}"
        print("Bước 5: POST lần 3 → 409 ✓ (chống review lặp)")
    finally:
        proc2.terminate()
        proc2.wait(timeout=30)

    with SessionLocal() as db:
        for table in ("correction_examples", "human_reviews"):
            db.execute(text(f"DELETE FROM {table} WHERE feedback_id = CAST(:f AS uuid)"),
                       {"f": str(fid)})
        for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            db.execute(text(f"DELETE FROM {table} WHERE thread_id = :t"), {"t": tid})
        db.query(Feedback).filter(Feedback.source == "hitl-evidence").delete(
            synchronize_session=False)
        db.commit()
    print("Dọn dẹp ✓ — TOÀN BỘ THỦ TỤC PASS (evidence #1 đạt)")


if __name__ == "__main__":
    main()

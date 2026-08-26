"""Generator bộ dữ liệu demo cho series agent — Phase 17 Task 2.

Chạy: uv run python scripts/generate_demo_dataset.py [--rows 650] [--weeks 6] [--out demo_dataset.csv]

Thành phần dữ liệu (toàn bộ GIẢ hoàn toàn, tiếng Việt trộn tiếng Anh):
- Baseline: 5 chủ đề trải đều `--weeks` tuần (jitter ±2 ngày, giờ hành chính).
- Planted emerging: ~40 row "không đăng nhập được bằng Google" dồn 5 NGÀY cuối
  → phase 14 phải flag is_emerging/is_spike.
- Planted false alarm: ~25 row "email thông báo tới trễ" bung giữa timeline rồi
  TẮT hẳn ≥3 tuần cuối → demo đường REJECT của agent.
- ~15% row baseline nhét PII giả (.example, đầu số 09xx) để pii_detected>0.

Lệch nhỏ so với chữ plan (đã ghi vào file plan): cột nội dung tên là `content`
(schema thật của import-csv — `_REQUIRED_COLUMNS = ("source", "content")`),
không phải `raw_content`. Thêm `--seed` (mặc định 17) để dataset tái lập được
cho bằng chứng luận văn.

Output CSV UTF-8, LF, cột: external_ref,source,created_at,content
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Ngân hàng nội dung GIẢ — mỗi chủ đề nhiều biến thể + mệnh đề đuôi ngẫu nhiên
# để tránh row trùng chữ từng chữ một (HDBSCAN sẽ bắt cặp sim≈1.0 vô nghĩa).
# ---------------------------------------------------------------------------

BASELINE_TOPICS: dict[str, list[str]] = {
    "tốc độ phản hồi chậm": [
        "App phản hồi cực chậm, đợi gần {n} giây mới ra kết quả.",
        "The response time is terrible, sometimes it takes {n} seconds to answer.",
        "Hỏi một câu đơn giản mà load mãi không xong, chậm quá chịu không nổi.",
        "Latency tăng hẳn sau bản cập nhật, mỗi câu hỏi phải đợi {n}s.",
        "Trả lời châm chím, trong khi bản trước nhanh lắm. Chậm như rùa.",
        "Speed issue: câu nào cũng delay {n} giây mới hiện text.",
        "Máy mạnh mạng ngon mà vẫn chậm, không hiểu bottleneck ở đâu.",
    ],
    "dịch thuật sai nghĩa": [
        "Dịch sai nghĩa câu hỏi của tôi, trả lời lệch hẳn chủ đề.",
        "Translation is wrong — it misunderstands my question half the time.",
        "Hỏi tiếng Việt nó dịch sang tiếng Anh rồi trả lời, sai nghĩa loạn xị.",
        "Sai nghĩa nặng: hỏi về refund mà nó hiểu thành return sản phẩm.",
        "Bản dịch tiếng Việt đọc rất gượng, nhiều chỗ sai ngữ pháp luôn.",
        "Nó hiểu nhầm từ đa nghĩa, dẫn đến câu trả lời sai meaning hoàn toàn.",
        "Translate mode cứ bị lỗi với câu dài, cắt ý và sai nghĩa.",
    ],
    "giọng đọc tự nhiên": [
        "Giọng đọc nghe robot quá, không tự nhiên chút nào.",
        "The voice sounds robotic, please make it more natural.",
        "Nghe giọng TTS cứ bị đứt quãng, không mượt như quảng cáo.",
        "Intonation phẳng lì, đọc số điện thoại thì còn tệ hơn.",
        "Giọng nữ nghe ổn nhưng giọng nam tự nhiên hơn thì tốt.",
        "Voice pausing bị lạ, ngắt nghỉ sai chỗ làm mất nghĩa câu.",
        "Mong thêm giọng miền Nam, giọng hiện tại nghe hơi cứng.",
    ],
    "giá gói premium": [
        "Giá gói premium cao quá so với tính năng đang có.",
        "Premium price is too high for students like me.",
        "Nâng cấp vip mà giới hạn query vẫn thấp, thấy không đáng tiền.",
        "So với đối thủ thì pricing đắt hơn hẳn, chưa thấy value tương xứng.",
        "Có nên giảm giá cho sinh viên không? Gói premium hơi sức ép.",
        "Price tăng lần thứ hai trong nửa năm mà feature chẳng thêm gì.",
        "Muốn trả rẻ hơn: nên có gói intermediate giữa free và premium.",
    ],
    "lỗi phát âm từ lạ": [
        "Phát âm sai các từ chuyên ngành, ví dụ 'quaternion' đọc loạn.",
        "It mispronounces unusual names and technical terms badly.",
        "Tên riêng nước ngoài bị đọc kiểu Việt hóa rất buồn cười.",
        "Từ viết tắt như API, SQL thì đọc ổn, nhưng từ hiếm thì sai pronunciation.",
        "Lỗi phát âm từ Hán Việt, đọc 'tr'/'s' lẫn lộn khiến khó nghe.",
        "Mispronunciation happens with acronyms longer than four letters.",
        "Đọc địa danh nước ngoài sai hết, cần cải thiện phần phonetics.",
    ],
}

EMERGING_TOPIC = "không đăng nhập được bằng Google trên app mobile"
EMERGING_TEMPLATES = [
    "Không đăng nhập được bằng Google trên app mobile, bấm nút nó báo lỗi ngay.",
    "Google sign-in fails on the mobile app — it shows an error popup every time.",
    "Login bằng tài khoản Google bị văng ra ngoài, thử cả iOS lẫn Android vẫn lỗi.",
    "Từ hôm qua không login được qua Google nữa, password login thì vẫn ok.",
    "App mobile đăng nhập Google stuck ở màn hình trắng rồi timeout.",
    "Sign in with Google returns error code 500 on app, web thì bình thường.",
    "Đăng nhập Google trên app bị lỗi ngay sau khi chọn tài khoản.",
    "Can't login via Google OAuth on mobile since the latest update.",
    "Nút Continue with Google nhấn không ăn, quay lại màn hình login mãi.",
    "Lỗi đăng nhập Google account trên app: vòng loading xoay rồi báo failed.",
]

BURST_TOPIC = "email thông báo tới trễ"
BURST_TEMPLATES = [
    "Email thông báo tới trễ gần một tiếng mới nhận được.",
    "Notification emails arrive very late, sometimes an hour after the event.",
    "Mail thông báo reset password tới trễ, ngồi chờ mãi không thấy.",
    "Email xác nhận giao dịch bị delay, đến tay khi nào không để ý nữa.",
    "Thông báo qua email chậm kinh khủng, check spam cũng không thấy.",
    "Delayed email alerts make the workflow annoying, please fix the queue.",
    "Email notification latency tăng vọt từ sáng nay, giờ vẫn chậm.",
    "Thư mời cộng tác gửi tới trễ mấy tiếng đồng hồ.",
]

FILLERS = [
    "Hy vọng đội ngũ xem sớm.",
    "Mình dùng bản iOS.",
    "Xảy ra trên cả Android.",
    "Đã thử reinstall mà vẫn vậy.",
    "Rất mong được sửa trong bản update tới.",
]

FAKE_NAMES = ["Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cương", "Phạm Mỹ Dung"]
PII_SENTENCE = (
    " Liên hệ mình nhé: {name}, email {email} hoặc gọi {phone}."
)


def _business_time(base: datetime, rng: random.Random) -> datetime:
    """Giờ hành chính 02:00–13:59 UTC (~09:00–20:00 giờ Việt Nam)."""
    return base.replace(
        hour=rng.randint(2, 13),
        minute=rng.randint(0, 59),
        second=rng.randint(0, 59),
        microsecond=0,
    )


def _pick(template_pool: list[str], rng: random.Random, seen: set[str]) -> str:
    """Chọn template + filler sao cho ít trùng lặp tuyệt đối nhất có thể."""
    for _ in range(6):
        text = rng.choice(template_pool)
        if rng.random() < 0.55:
            text += " " + rng.choice(FILLERS)
        text = text.format(n=rng.randint(5, 60))
        if text not in seen:
            return text
    return text  # chấp nhận trùng nếu pool cạn


def generate(
    rows: int,
    weeks: int,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    window_start = now - timedelta(days=weeks * 7)

    emerging_count = min(40, max(rows // 8, 10))
    burst_count = min(25, max(rows // 12, 8))
    baseline_count = max(rows - emerging_count - burst_count, len(BASELINE_TOPICS))

    def stamp(moment: datetime) -> datetime:
        """Giờ hành chính; nếu bị đẩy quá `now` thì lùi 1 ngày (vẫn trong cửa sổ)."""
        t = _business_time(moment, rng)
        return t - timedelta(days=1) if t > now else t

    records: list[tuple[datetime, str]] = []  # (created_at, content)
    seen: set[str] = set()

    # --- Baseline: chia đều 5 chủ đề, trải đều cửa sổ ---
    per_topic = baseline_count // len(BASELINE_TOPICS)
    leftovers = baseline_count - per_topic * len(BASELINE_TOPICS)
    span_seconds = int((now - window_start).total_seconds())
    for topic_index, templates in enumerate(BASELINE_TOPICS.items()):
        _, pool = templates
        count = per_topic + (1 if topic_index < leftovers else 0)
        for _ in range(count):
            offset = rng.randint(0, span_seconds)
            moment = window_start + timedelta(seconds=offset)
            content = _pick(pool, rng, seen)
            # ~15% row baseline nhét PII giả có chủ đích
            if rng.random() < 0.15:
                content += PII_SENTENCE.format(
                    name=rng.choice(FAKE_NAMES),
                    email=f"{rng.choice(['thao','hung','mai','duc'])}{rng.randint(1,99)}@gmail.example",
                    phone=f"09{rng.randint(10000000, 99999999)}",
                )
            records.append((stamp(moment), content))

    # --- Planted emerging: dồn vào 5 NGÀY cuối ---
    emerge_start = now - timedelta(days=5)
    for _ in range(emerging_count):
        offset = rng.randint(0, int((now - emerge_start).total_seconds()))
        moment = emerge_start + timedelta(seconds=offset)
        records.append((stamp(moment), _pick(EMERGING_TEMPLATES, rng, seen)))

    # --- Planted false alarm: bung ~10 ngày giữa timeline, TẮT hẳn ≥3 tuần cuối ---
    burst_end_cap = now - timedelta(days=21)
    burst_start_floor = window_start + timedelta(days=2)
    burst_end = max(burst_end_cap, burst_start_floor + timedelta(days=3))
    burst_start = max(burst_start_floor, burst_end - timedelta(days=10))
    for _ in range(burst_count):
        offset = rng.randint(0, int((burst_end - burst_start).total_seconds()))
        moment = burst_start + timedelta(seconds=offset)
        records.append((stamp(moment), _pick(BURST_TEMPLATES, rng, seen)))

    # Sắp theo thời gian rồi đánh external_ref tuần tự → ref tăng cùng thời gian
    records.sort(key=lambda pair: pair[0])
    sources = ["app_review", "email", "web_form"]
    return [
        {
            "external_ref": f"demo-{i:05d}",
            "source": sources[i % len(sources)],
            "created_at": moment.isoformat(),
            "content": content,
        }
        for i, (moment, content) in enumerate(records)
    ]


def verify(csv_path: Path, rows_expected: int, weeks: int) -> None:
    """Verify offline (Step 2.3): parse lại bằng DictReader + kiểm tra cửa sổ."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=weeks * 7 + 1)
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == [
            "external_ref",
            "source",
            "created_at",
            "content",
        ], f"Sai header: {reader.fieldnames}"
        parsed = list(reader)
    assert len(parsed) == rows_expected, f"{len(parsed)} != {rows_expected}"
    for row in parsed:
        moment = datetime.fromisoformat(row["created_at"])
        assert window_start <= moment <= now, f"Ngoài cửa sổ: {row['created_at']}"
        assert row["content"].strip(), "Row rỗng"
    print(f"[verify] OK: {len(parsed)} row, header đúng, mọi created_at trong cửa sổ {weeks} tuần.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sinh bộ dữ liệu demo (plan 17 Task 2).")
    parser.add_argument("--rows", type=int, default=650, help="Tổng số row (default 650).")
    parser.add_argument("--weeks", type=int, default=6, help="Độ rộng cửa sổ thời gian, tuần (default 6).")
    parser.add_argument("--out", type=Path, default=Path("demo_dataset.csv"), help="File CSV xuất ra.")
    parser.add_argument("--seed", type=int, default=17, help="Seed RNG để tái lập được.")
    args = parser.parse_args()

    records = generate(args.rows, args.weeks, args.seed)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["external_ref", "source", "created_at", "content"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    pii_like = sum(1 for r in records if "@gmail.example" in r["content"])
    emerging_rows = sum(1 for r in records if any(t in r["content"] for t in EMERGING_TEMPLATES[:3]))
    print(f"[generate] {args.out}: {len(records)} row | PII-like ~{pii_like} | "
          f"emerging ~{emerging_rows} (Google-login) | seed {args.seed}")
    verify(args.out, len(records), args.weeks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# AI Feedback Agent — Khóa luận

**"AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI"**

Pipeline: PII sanitize → LLM classify → embed (pgvector) → cluster → trend/emerging/spike → insight → HITL review.
Giai đoạn **Backend foundation** đã HOÀN THÀNH (2026-08-25) — kết quả chi tiết:
[`docs/backend-foundation-report.md`](docs/backend-foundation-report.md).

## Quickstart — fresh machine (Windows, không Docker)

> Yêu cầu sẵn: tài khoản **Supabase** (free tier), Python 3.12 + [uv](https://docs.astral.sh/uv/).
> ⚠️ Free tier Supabase tự **pause sau 7 ngày** low-activity — mỗi tuần mở dashboard hoặc chạy ≥1 query bất kỳ, nếu không mọi lệnh dưới đây sẽ lỗi kết nối.

```powershell
# 0. Tạo Supabase project (một lần, trên trình duyệt)
#    Dashboard → Connect → Session pooler → copy connection string
#    Region: Singapore (gần VN). EU (Frankfurt) nếu muốn khớp Langfuse EU.

# 1. Clone repo + tạo .env từ mẫu, điền key thật (KHÔNG commit .env)
cp .env.example backend/.env     # Windows: Copy-Item .env.example backend\.env

# 2. Cài dependencies (từ backend/)
cd backend
uv sync                          # Python 3.12 do uv quản lý tự động

# 3. Migrate schema lên Supabase
uv run alembic upgrade head      # idempotent — `alembic current` phải ra "(head)"

# 4. Seed 2 user mặc định (idempotent upsert theo email)
uv run python scripts/seed_users.py
#    ⚠️ đặt SEED_PM_PASSWORD / SEED_OPS_PASSWORD để tránh mật khẩu dev mặc định

# 5. Chạy API — uvicorn chạy RIÊNG MỘT terminal, KHÔNG spawn từ script khác
uv run uvicorn app.main:app --reload

# 6. Kiểm tra sức khỏe
curl http://127.0.0.1:8000/api/health
#    {"status":"ok","db":"ok","pii_mode":"full", ...}
```

Swagger UI: `http://127.0.0.1:8000/docs` — bấm *Authorize*, đăng nhập
`pm@thesis.local` / mật khẩu đã seed (hoặc lấy token từ `POST /api/auth/token`
và dán Bearer header — hai cơ chế song song, cookie ưu tiên).

## Chạy local nhanh — Backend + Frontend

Sau lần cài đặt đầu tiên, mở **hai terminal riêng** tại thư mục gốc repo:

```powershell
# Terminal 1 — Backend API (giữ terminal này chạy)
cd backend
uv run uvicorn app.main:app --reload

# Terminal 2 — Frontend Next.js (giữ terminal này chạy)
cd frontend
pnpm dev
```

Mở ứng dụng tại `http://127.0.0.1:3000/landing`; API health check là
`http://127.0.0.1:8000/api/health`, Swagger là `http://127.0.0.1:8000/docs`.

Nếu đây là máy mới, cài frontend một lần trước khi chạy: `cd frontend; pnpm install`.
Backend cần `backend/.env` hợp lệ và Supabase đang active (xem Quickstart ở trên).
Nhấn `Ctrl+C` trong từng terminal để dừng service tương ứng.

Sau khi đăng nhập, queue import/analysis nằm trong capsule **Hoạt động** bên
phải navbar. Upload CSV chỉ tạo preview miễn phí; mapping AI và analysis đều
có receipt + bước xác nhận riêng, nên không tự tiêu credit. Có thể reload hoặc
chia sẻ URL `?activity=import:<id>` / `?activity=run:<id>` để tiếp tục review.

## Ma trận test

| Lệnh | Phạm vi | Yêu cầu |
|---|---|---|
| `uv run pytest -q` | Unit thuần — mock LLM/embedder/tracing | Không cần DB/network |
| `uv run pytest -q -m integration` | Integration trên PostgreSQL thật; provider AI vẫn mock | Supabase active + internet |
| `TEST_DATABASE_URL=… uv run pytest -q -m integration` | Trỏ suite sang **test project thứ 2** (khuyến nghị khi data demo đã quan trọng); phải `alembic upgrade head` một lần trên project đó | Project test đang active |

- Test integration mà DB không reachable → **SKIP kèm message rõ**, không ERROR.
- Suite integration TỰ DỌN row mình tạo (tiền tố `external_ref` + quarantine);
  vẫn chạy an toàn trên DB dev dùng chung.
- Chi tiết chiến lược: [`backend/tests/conftest.py`](backend/tests/conftest.py)
  và decision log ngày 2026-08-25 (Phase 11).

## Quy tắc vận hành cần nhớ

1. **Không Docker** dưới mọi hình thức — FastAPI native Windows + Supabase managed PG.
2. `uvicorn --reload` chạy riêng terminal (Windows quirk §10.2 execute-plan).
3. **PII boundary**: raw content không bao giờ vào prompt/log/trace/docs hoặc
   API response; chỉ `feedback_text` và profile/sample đã sanitize ra khỏi biên.
4. File `.env` nằm ở repo root VÀ copy tại `backend/.env` — code đọc bản trong `backend/`.
5. Mọi lệch khỏi plan → entry dated trong [`docs/decisions.md`](docs/decisions.md).

## Deploy VPS (phase sau — placeholder)

Giai đoạn backend foundation CHƯA bao gồm deploy. Kế hoạch hướng tới (khóa luận):
VPS nhỏ (2GB RAM đủ cho presidio full-mode ~1GB), uvicorn + nginx reverse proxy,
`.env` prod với `APP_ENV=prod` + `SECRET_KEY` thật (bắt buộc — thiếu sẽ từ chối khởi động),
Supabase giữ nguyên làm managed DB. Sẽ được phân rã thành plan riêng khi bắt đầu giai đoạn UI.

## Tài liệu

| File | Dành cho |
|---|---|
| [`AGENTS.md`](AGENTS.md) | AI coding agent — ngữ cảnh đứng, stack đã chốt, quy tắc cứng |
| [`docs/backend-foundation-execute-plan.md`](docs/backend-foundation-execute-plan.md) | Kế hoạch gốc giai đoạn vừa hoàn thành |
| [`docs/plans/00-index.md`](docs/plans/00-index.md) | Phân rã 12 phase + trạng thái thực thi |
| [`docs/api-checklist.md`](docs/api-checklist.md) | Bản đồ endpoint đã ship + quy tắc sync khi thêm/sửa API (thay `api-notes.md` không từng tồn tại — decisions 2026-08-26) |
| [`docs/backend-foundation-report.md`](docs/backend-foundation-report.md) | Kết quả DoD sweep — tư liệu chương khóa luận |
| [`docs/decisions.md`](docs/decisions.md) | Decision Log — mọi lệch khỏi plan |

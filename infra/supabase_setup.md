# Supabase Setup — note thiết lập 1 lần (amendment v1.1)

> Nguồn: docs/plans/01-preconditions-environment.md §2.1 · Quyết định gốc: docs/decisions.md 2026-08-23 (Supabase thay WSL2-PG)
> File này là **note vận hành**, không chứa password/key thật.

## 1. Tạo project

1. Đăng nhập <https://supabase.com/dashboard> → **New project**.
2. **Region: Singapore** (`aws-0-ap-southeast-1`) — gần VN, latency thấp nhất; hoặc EU nếu muốn cùng region với Langfuse EU.
3. **Database Password**: đặt mạnh, lưu NGAY vào password manager. Quên = phải reset (làm gián đoạn mọi môi trường đang nối).

## 2. Lấy connection string (SESSION POOLER — bắt buộc)

Dashboard → **Connect** → tab **Session pooler** → copy URI dạng:

```
postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Khi điền vào `backend/.env` → **đổi scheme thành `postgresql+psycopg://`** (driver SQLAlchemy).

⚠️ **KHÔNG dùng** transaction pooler (port `6543`) — phá prepared statements của Alembic/psycopg.
Direct connection `db.<ref>.supabase.co:5432` chỉ dùng khi mạng hỗ trợ IPv6 tốt — mặc định ưu tiên pooler.

## 3. Extension pgvector

Cách khuyến nghị: chạy 1 lần trong Dashboard → **SQL Editor**:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- Bare, **không pin version** (Supabase deprecated extension pinning từ 2026-08-05).
- Supabase đặt extension vào schema `extensions` (quy ước) — engine phía app sẽ đặt `options=-csearch_path=extensions,public`.
- Alembic migration đầu của phase 03 cũng có bước tạo extension idempotent — chạy SQL Editor trước chỉ để chắc tay.

## 4. Quy tắc anti-pause (free tier)

Free tier **tự pause sau 7 ngày low-activity**. Mỗi tuần PHẢI một trong hai:

- mở dashboard project bất kỳ, hoặc
- chạy ≥1 query (vd: `uv run python -c "import os,psycopg;c=psycopg.connect(os.environ['DATABASE_URL']);print(c.execute('select 1').fetchone())"`).

Nếu quên và bị pause: Dashboard → **Resume** (dữ liệu giữ nguyên; mất vài phút khởi động lại).

## 5. Checklist trạng thái

- [ ] Project tạo xong, region đã chọn
- [ ] Password đã vào password manager
- [ ] Session pooler URI đã điền `backend/.env` (scheme `postgresql+psycopg://`)
- [ ] `CREATE EXTENSION vector` đã chạy trong SQL Editor
- [ ] Nhắc lịch weekly anti-pause đã đặt

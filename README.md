# AI Feedback Agent — Khóa luận

**"AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI"**

Pipeline: PII sanitize → LLM classify → embed (pgvector) → cluster → trend/emerging/spike → insight → HITL review.

## Giai đoạn hiện tại

**Backend foundation** — chưa có UI. Toàn bộ kế hoạch thực thi nằm ở:

📄 [`docs/plans/backend-foundation-execute-plan.md`](docs/plans/backend-foundation-execute-plan.md)

## Quickstart (tóm tắt — chi tiết đầy đủ trong plan §3–§4 và `docs/plans/backend-foundation/`)

> Yêu cầu sẵn: tài khoản **Supabase** (free tier), Python 3.12 + uv, Node không cần ở giai đoạn này. Lưu ý: free tier Supabase tự pause sau 7 ngày không hoạt động — mỗi tuần mở dashboard hoặc chạy ≥1 query.

```bash
# 1. Tạo Supabase project (chạy một lần, trên trình duyệt)
#    Region: Singapore (gần VN) hoặc EU. Dashboard → Connect → Session pooler
#    → copy connection string vào DATABASE_URL của .env

# 2. Backend deps (terminal Windows, từ thư mục backend/)
cd backend && uv sync

# 3. Env: copy và điền keys thật
cp ../.env.example .env

# 4. Migrate + seed + chạy
uv run alembic upgrade head
uv run python scripts/seed_users.py
uv run uvicorn app.main:app --reload   # chạy RIÊNG một terminal
```

> ⚠️ Các bước trên khả dụng sau khi agent thực thi plan xong milestone tương ứng (`infra/supabase_setup.md`, `scripts/seed_users.py` do agent tạo).

## Tài liệu

| File | Dành cho |
|---|---|
| [`AGENTS.md`](AGENTS.md) | AI coding agent — ngữ cảnh đứng, stack đã chốt, quy tắc cứng |
| [`docs/plans/backend-foundation-execute-plan.md`](docs/plans/backend-foundation-execute-plan.md) | Kế hoạch thực thi giai đoạn hiện hành |
| [`docs/decisions.md`](docs/decisions.md) | Decision Log — mọi lệch khỏi plan phải ghi tại đây |

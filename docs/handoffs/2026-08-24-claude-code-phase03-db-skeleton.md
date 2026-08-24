# Handoff: Phase 03 done — repo skeleton + 8 models + Alembic baseline verified on Supabase
- Date: 2026-08-24 21:45 local
- From: claude-code
- To: any
- Branch / worktree: main (repo root, per user's standing instruction — no worktree)
- Milestone: docs/plans/03-repo-skeleton-models-migrations.md
- Status: done

## Done
- Full app skeleton under `backend/app/`: core (config/logging/security-placeholder), db (session/base), models ×8, main.py factory, api/routes/admin.py (5× 501 stubs), health endpoint.
- Settings: pydantic-settings với AliasChoices (`DATABASE_URL`|`DB_CONNECT_STRING`, `EMBEDDING_DIM`|`EMBEDDING_DIMENSIONS`) per decisions 2026-08-24; `database_url_sqla` property percent-encodes userinfo tách ở `@` cuối.
- 3 hand-written migrations (0001 extension+users, 0002 feedbacks/runs/logs, 0003 future tables) — viết tay thay vì autogenerate vì cần chia đúng nhóm logic của plan; chất lượng kiểm chứng bằng autogenerate-diff-rỗng sau upgrade.
- decisions.md: 4 entries mới (enum chốt, set_main_option %, PgBouncer strips options, + ghi chú đếm enum 8 chứ không phải 7).
- 00-index.md: tick phase 01, 02, 03.

## Evidence
- `uv run python -c "from app.main import app; ..."` → TABLES 8 metadata ✓
- `uv run uvicorn app.main:app --port 8123` → `curl /api/health` = `{"status":"ok","app_env":"dev"}`; `/api/clusters` = HTTP 501 ✓
- `uv run alembic upgrade head` → 0003 head ✓
- Query Supabase: public có đủ 8 bảng + alembic_version; `pg_extension` có `vector`; 8 enum types ở schema public, giá trị ai_issue/sentiment đúng entry dated ✓
- `alembic downgrade base` + `upgrade head` lại → sạch, về 0003 ✓
- Fake table `checkpoints` tạo tay → `alembic revision --autogenerate -m verify_no_diff` sinh file chỉ có `pass/pass` (filter hoạt động, models khớp DB) — file đã xóa sau test, bảng giả đã drop ✓
- PII scan trên diff: không lệnh log/print nào nhận payload content (chỉ comment cảnh báo) ✓

## Not done / gaps
- Không có trong scope phase. `auth.users` thấy khi query information_schema là bảng hệ thống Supabase Auth — KHÔNG phải rác, đừng xóa.
- Test suite pytest thuộc Phase 11 (plan không yêu cầu test riêng cho phase này).

## Blocked / risks
- ⚠️ **Password DB đã lộ vào transcript phiên này** (traceback in connection string khi debug lỗi configparser). Khuyến nghị người dùng reset database password Supabase (Dashboard → Project Settings → Database) rồi cập nhật `backend/.env`. Xem decisions.md entry "set_main_option".
- Supabase free tier anti-pause: chạy ≥1 query mỗi <7 ngày (vừa migrate xong hôm nay).

## Next steps
1. Người dùng: reset DB password (xem risk ở trên), copy `.env` từ root vào `backend/.env` nếu bị mất lần nữa (file root `.env` hiện vẫn còn giữ nguyên).
2. Phase 04 (auth + RBAC): docs/plans/04-auth-rbac.md — triển khai `core/security.py` (argon2 + JWT cookie), `api/deps.py`, routes auth, `scripts/seed_users.py`.
3. Khi deploy VPS (nối thẳng không qua pooler): connect_args search_path sẽ áp dụng thật — rà lại entry "PgBouncer strips options" trước khi tin rằng nó vô hại vĩnh viễn.

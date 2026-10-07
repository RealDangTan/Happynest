# Handoff — CRUD quản lý đầy đủ (Vault · Reports · Products · Imports)

- **Agent:** claude-code · **Ngày:** 2026-09-16 · **Nhánh:** `codex/activity-center`
- **Plan:** `~/.commandcode/plans/crud-management-screens.md` (đã duyệt qua plan review; owner chọn: full CRUD 4 thực thể · hard delete · pm-only)

## Đã làm

- **BE (Phase A+B):** thêm 7 endpoint destructive — `PATCH/DELETE /api/feedbacks/{id}`, `POST /api/feedbacks/bulk-delete`, `DELETE /api/imports/{id}`, `PATCH/DELETE /api/insights/{id}`, `DELETE /api/products/{id}` (cascade đa bảng trong 1 transaction). Guard `require_role("pm")` per-route; router-level giữ pm|operations cho GET/POST. Text feedback sửa → re-sanitize (Presidio) + embedding NULL. Insight PATCH ghi trail `insight_reviews` (action=edit) + status `edited`. Files: `routes/feedback.py`, `routes/imports.py`, `routes/products.py`, `routes/agent.py`, `schemas/feedback.py`, `schemas/agent.py`.
- **FE (Phase C+D):** hooks mới (`useUpdateFeedback/useDeleteFeedback/useBulkDeleteFeedbacks/useDeleteImport/useUpdateInsight/useDeleteInsight/useDeleteProduct`); Vault: edit dialog + delete đơn/bulk + xoá import batch (confirm); Reports: Edit/Delete report; breadcrumb: Rename + Delete product (typed-name confirm). Tất cả ẩn với role operations.
- **Docs:** `docs/api-checklist.md` — section "Bổ sung CRUD quản lý — 2026-09-16" + sửa auth PATCH products → pm-only.

## Verification (bằng chứng)

- `uv run pytest -m integration tests/test_crud_management.py` → **12/12 passed** (TDD RED→GREEN; suite tự seed product riêng + teardown)
- `uv run pytest -m "not integration"` → **81 passed**
- FE: typecheck ✓ · vitest 39/39 ✓ · `pnpm build` ✓
- Backend dev server đã restart (port 8000) — `/api/health` ok. Lưu ý: PATCH products đổi guard pm-only.

## Rủi ro / next steps

- Full pytest suite (có integration) chạy rất lâu trên máy dev (>15 phút, warmup LLM/stanza per worker) — session này chạy unit-only + suite CRUD; nên chạy full suite 1 lần khi rảnh.
- Xoá product cascade xoá cả `analysis_runs` gắn import của product; understand-runs (không gắn import) KHÔNG bị xoá — có thể cân nhắc sweep sau.
- Chưa commit (workspace có thay đổi song song của session khác) — owner quyết định commit theo phase khi review.

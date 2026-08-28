# Handoff: FE-08 auth register + logout (Google ghost)
- Date: 2026-08-28 00:50 local
- From: claude-code
- To: any
- Branch / worktree: main (shared working tree — CẢNH BÁO: voc-os rewrite đang dở ở tree này)
- Milestone: docs/plans/FE-08-auth-register-google.md (P1.5)
- Status: in-progress (FE verify xong, BE pytest BLOCKED)

## Done
- BE: `POST /api/auth/register` (role luôn `operations`, 201/409/422, email lowercase,
  validate bằng Pydantic pattern — KHÔNG thêm email-validator) + `POST /api/auth/logout`
  (xoá cookie Max-Age=0, 204 idempotent) trong `backend/app/api/routes/auth.py`,
  schema `RegisterIn` trong `backend/app/schemas/auth.py`.
- BE tests: `TestRegister` (6) + `TestLogout` (2) thêm trong `backend/tests/test_auth.py` —
  VIẾT TRƯỚC code (TDD) nhưng CHƯA CHẠY được (xem Blocked).
- FE: trang `/register` (email + mật khẩu + xác nhận, lỗi client-side tiếng Việt,
  đăng ký xong tự login qua `/api/auth/token` rồi vào `/feedbacks`); nút Google ghost
  (disabled, title "Sắp có") + separator + link qua lại trên cả `/login` và `/register`;
  logout = DropdownMenu trên avatar sidebar footer (`(app)/layout.tsx`) → POST logout →
  `queryClient.clear()` → `/login`; middleware thêm `/register` vào PUBLIC_PATHS.
- Docs: plan FE-08 viết JIT, FE-00-index tick + log, api-checklist +2 dòng (24→26).

## Evidence
- FE: `pnpm typecheck` sạch; `pnpm test` 10/10; `pnpm build` xanh 11 route (`/register` có mặt).
- BE: pytest KHÔNG chạy nổi (xem Blocked) — code route/schema CHƯA được verify runtime.
- git status trước khi commit: tree có hàng loạt `D` staged + model mới (import_, product)
  của phiên voc-os rewrite — không đụng, commit pathspec chỉ file của FE-08.

## Blocked / risks
- `uv run pytest tests/test_auth.py` chết ngay khi load conftest:
  `ImportError: cannot import name 'correction_example' from partially initialized module 'app.models'`.
  Nguyên nhân: `backend/app/db/base.py` (dòng 25–34) vẫn import `correction_example`,
  `human_review`, `insight` nhưng các model này đã bị xoá trong working tree bởi
  voc-os rewrite (series 21–27) đang dở. KHÔNG sửa hộ — phiên rewrite sẽ cập nhật
  `base.py` theo `app/models/__init__.py` mới. Khi rewrite ổn định: chạy lại
  `uv run pytest tests/test_auth.py` (8 test mới phải PASS, cần DB Supabase).
- Google OAuth thật chưa làm — chờ owner có client ID/secret (docs/google-oauth-setup.md).
- Backend :8000 nếu còn chạy thì là bản cũ (không --reload) — phải restart mới thấy /register.

## Next steps
1. Sau khi voc-os rewrite land: chạy `uv run pytest tests/test_auth.py` verify 8 test.
2. Live verify kịch bản: đăng ký user mới qua `/register` → tự vào `/feedbacks`;
   trùng email → alert 409; logout → cookie xoá, quay lại `/login`.
3. P1.5 phần Google: làm backend OAuth2 authorization-code + nút bỏ disabled.

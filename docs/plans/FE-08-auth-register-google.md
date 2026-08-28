# FE-08 — Auth mở rộng: Register + Logout (+ Google ghost)

**Goal:** Người dùng tự tạo tài khoản từ UI, đăng xuất được. Google login chỉ để nút ghost (disabled) — làm thật khi owner có client ID/secret (P1.5 gốc, tách phần Google ra sau).

**Core principle:** register là endpoint public duy nhất được tạo user, và nó luôn tạo role `operations` — không ai tự đăng ký làm `pm`.

## Thiết kế

- **BE `POST /api/auth/register`** — `{email, password}` JSON → `201 UserOut` (role `operations`). Email normalize lowercase; trùng email → 409; email sai dạng / mật khẩu < 8 ký tự → 422. Validate bằng Pydantic pattern (KHÔNG thêm `email-validator` — tránh lệch pin, Hard rule 3).
- **BE `POST /api/auth/logout`** — xoá cookie `access_token` (Max-Age=0), trả 204, idempotent.
- **FE `/register`** — email + mật khẩu + xác nhận mật khẩu; submit xong tự login (gọi lại `/api/auth/token`) rồi vào `/feedbacks`. Nút "Đăng nhập với Google" ghost disabled với title "Sắp có".
- **FE `/login`** — thêm nút Google ghost + link "Chưa có tài khoản? Đăng ký".
- **FE logout** — avatar ở sidebar footer bọc `DropdownMenu`, item "Đăng xuất" → POST logout → xoá query cache → `/login`.
- **Middleware** — thêm `/register` vào `PUBLIC_PATHS`; đã login vào `/register` → redirect `/feedbacks` (giống `/login`).

## Tasks

1. [ ] BE: test register + logout (TDD RED) trong `tests/test_auth.py` → route + schema (GREEN)
2. [ ] FE: trang `/register` + nút Google ghost (login + register)
3. [ ] FE: logout menu sidebar + middleware `/register`
4. [ ] Docs: api-checklist (+2 dòng), FE-00-index tick

## Không làm

- Google OAuth thật (chờ GCP credentials — [guide](../google-oauth-setup.md))
- Forgot/reset password, refresh token (backlog)
- Chống spam đăng ký (rate limit) — demo luận văn

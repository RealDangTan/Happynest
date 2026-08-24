# Phase 04 — Auth & RBAC

> **Nguồn:** execute-plan §1 (Auth) + §7 (routes auth) + DoD mục 2
> **Trạng thái:** ⬜ · **Blocked by:** Phase 03
> **Commit mẫu:** `feat(auth): oauth2 password flow, jwt cookie, role guard, seed users`

## 1 · Mục tiêu

Đăng nhập bằng OAuth2 password flow do FastAPI sở hữu, JWT trong httpOnly SameSite=Lax cookie, hai role `pm` | `operations`, route chặn sai role bằng 403. **Register DISABLED** (không có route đăng ký công khai). Next.js sau này sẽ proxy — route phải sạch tiền tố `/api/*`.

## 2 · Việc CON NGƯỜI

- Không có. (Nếu muốn đổi mật khẩu seed: truyền biến môi trường lúc chạy seed script.)

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 `app/core/security.py`
- `hash_password(p) -> str` / `verify_password(p, h) -> bool` qua `pwdlib` với argon2.
- `create_access_token(sub: str, role: str) -> str`: pyjwt HS256, claim `sub` = user id, `role`, `exp` = now + 12h, `iat`.
- `decode_token(t) -> dict` — raise `jwt.PyJWTError` cho caller bắt.

### 3.2 Schemas — `app/schemas/auth.py`
- `TokenOut{access_token:str, token_type:"bearer"}` (trả body cho tiện test, dù auth thật nằm ở cookie).
- `UserOut{id, email, role}`.

### 3.3 Deps — `app/api/deps.py`
- `get_db()` yield session (từ `SessionLocal`), đóng trong finally.
- `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")`.
- `get_current_user(token=Depends(oauth2_scheme)) -> User`: decode → load user theo id từ DB; 401 nếu token hỏng/hết hạn/user không tồn tại.
- `require_role(*roles)` factory → dependency ném `HTTPException 403` nếu `user.role` ngoài danh sách. Dùng kiểu `Depends(require_role("pm","operations"))`.

### 3.4 Routes — `app/api/routes/auth.py`
- `POST /api/auth/token`: nhận `OAuth2PasswordRequestForm` (username=email) → verify argon2 → set cookie `access_token`, `httponly=True`, `samesite="lax"`, `secure=(APP_ENV=="prod")`, path=`/` → trả `TokenOut`. Sai thông tin → **401** (không tiết lộ email tồn tại hay không).
- `GET /api/auth/me`: `UserOut` của current user.
- Register: KHÔNG tạo route; nếu cần ghi chú thì để docstring trong router giải thích "register disabled — chỉ seed script tạo user".
- Cookie name trùng field OAuth2 mặc định để Swagger "Authorize" hoạt động được với cookie.

### 3.5 Seed — `backend/scripts/seed_users.py`
- Idempotent (upsert theo email): `pm@thesis.local` role `pm`, `ops@thesis.local` role `operations`.
- Mật khẩu đọc env `SEED_PM_PASSWORD` / `SEED_OPS_PASSWORD`, fallback giá trị dev mặc định + **in cảnh báo đổi ngay** khi dùng fallback.
- Chạy: `uv run python scripts/seed_users.py`.

### 3.6 Tests — `backend/tests/test_auth.py`
- Fixture client (TestClient) + DB test (chiến lược chung ở `conftest.py`, hoàn thiện Phase 11 — bây giờ đủ dùng được):
  - login đúng → 200 + cookie httpOnly tồn tại;
  - login sai pass → 401;
  - `/api/auth/me` kèm cookie → đúng user;
  - route guard demo (dùng chính `/me` hoặc endpoint Phase 05): thiếu/sai role → 403.

## 4 · Tiêu chí nghiệm thu (map DoD)

| DoD | Bằng chứng |
|---|---|
| Login cả 2 role seeded thành công | output curl/test |
| Route guarded trả 403 với role sai | test assert |
| Không route register | review diff |
| Password hash argon2 (kiểm tra prefix `$argon2`) trong DB | query tay |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run python scripts/seed_users.py
uv run uvicorn app.main:app   # terminal riêng khi dùng --reload
# terminal khác:
curl -i -X POST http://localhost:8000/api/auth/token -d "username=pm@thesis.local&password=<pass>" -H "Content-Type: application/x-www-form-urlencoded"
curl -s http://localhost:8000/api/auth/me -H "Cookie: access_token=<token>"
uv run pytest tests/test_auth.py
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Swagger UI không authorize được vì cookie-based | Ghi chú dùng endpoint `/token` trả body token + header Bearer cho test; entry nhỏ nếu thêm cơ chế chấp nhận `Authorization: Bearer` song song |
| pwdlib/argon2 wheel lỗi Windows | Entry dated; thử `pwdlib[argon2]` version khác hoặc `argon2-cffi` pin mới |
| Cần exp ngắn hơn/dài hơn 12h | Chỉnh constant, ghi vào api-notes.md (không cần decisions.md) |

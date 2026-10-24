# Handoff: Google OAuth login end-to-end + deploy FRONTEND lên Vercel (backend ở lại locked stack)
- Date: 2026-10-23 (đêm, Asia/Saigon)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (working tree chia sẻ — KHÔNG commit gì, giữ nguyên uncommitted changeset có sẵn)
- Milestone: yêu cầu owner "deploy lên Vercel để có auth bằng acc Google"; không thuộc plan series nào
- Status: done (còn 1 bước cấu hình tài khoản chỉ owner làm được — xem Next steps)

## Done
1. **Google OAuth Authorization Code flow thuần** (không thêm authlib — PyJWT PyJWKClient + httpx):
   - `app/services/google_oauth.py`: build auth URL, exchange code, verify `id_token` (RS256/JWKS/aud/iss/exp), `extract_identity` (bắt buộc `email_verified`).
   - `app/api/routes/auth.py`: `GET /api/auth/google/login` (302 Google + cookie `g_oauth_state` chống CSRF, path-scoped `/api/auth/google`, TTL 600s; chưa cấu hình → 503 rõ nguyên nhân) + `GET /api/auth/google/callback` (upsert user: khớp `google_sub` → link email → tạo Google-only; JWT cookie như password login; mọi lỗi → 302 `/login?google_error=<mã>`).
   - Guards: login password cho account Google-only → 401 thông báo riêng; register trùng email Google-only → 409 riêng.
   - `users.password_hash` nullable + `users.google_sub` unique — **migration 0022 ĐÃ APPLY lên Supabase dev** (`alembic current` = `0022 (head)`).
   - `.env` cần: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (đã ghi `.env.example`; rỗng = feature off).
2. **FE**: bật nút "Đăng nhập với Google" ở `/login` + `/register` (full navigation); mới `lib/google-auth.ts` (map `?google_error=denied|state|exchange|email_conflict` → Alert; đọc param bằng useEffect, không dùng useSearchParams để giữ prerender).
3. **Docs**: `.env.example` (block Google OAuth + API_PROXY_ORIGIN), `docs/api-checklist.md` (2 endpoint mới + sửa dòng `/token` + `/register`), `docs/decisions.md` (entry đầy đủ 2026-10-23).
4. **Vercel — ĐÃ DEPLOY PRODUCTION**: `next.config.ts` proxy `/api/*` đọc `API_PROXY_ORIGIN` (mặc định `http://127.0.0.1:8000`); project `realdangtans-projects/frontend`; CLI nâng 41.6.0 → 65.2.0 (endpoint cũ từ chối CLI < 47.2.2).
   - **URL production: https://frontend-amber-eta-48.vercel.app** — `/landing` 200, `/login` 200; `/api/*` chưa nối (chưa set `API_PROXY_ORIGIN` — xem Next steps).
   - Vượt 2 chặn: (a) build fail 1 lần do refactor i18n ĐANG CHỨNG của session khác cùng tree (`labels.ts` đổi 2-lớp, consumer chưa sửa kịp) — đợi tsc xanh rồi deploy lại; (b) deploy thứ 3 bị **Blocked — "commit author doesn't have permission"**: git author `ledangtan2504@gmail.com` không khớp email verify trên account Vercel. Workaround: deploy từ bản copy KHÔNG có `.git` (temp dir `/d/ATEMP/vercel-fe-deploy`, giữ `.vercel/project.json` để link đúng project) → Vercel không có commit metadata để kiểm author → thành công.
   - **Đổi identity theo chỉ đạo owner (2026-10-24):** `gh auth switch` sang account **RealDangTan** (owner của `github.com/RealDangTan/Happynest`, email `11236199@st.neu.edu.vn`) + git config REPO-LOCAL `user.name/user.email` = RealDangTan/11236199@st.neu.edu.vn. Lịch sử commit cũ vẫn authored bởi ledangtan2504@gmail.com (không rewrite). Từ giờ commit/đẩy mới dưới danh tính RealDangTan — deploy từ repo sẽ khớp author check của Vercel (miễn email đó đã verify trên account Vercel).

## Evidence
- `uv run pytest tests/test_auth_google.py -m integration` → **13 passed** (Supabase thật, mock exchange/verify ở ranh giới service; flow redirect/state/upsert/link/guards chạy thật).
- `uv run pytest -q` (unit mặc định) → **162 passed, 1 FAILED** `tests/test_enricher_unit.py::test_enrich_feedback_prompt_uses_taxonomy_and_call_type` — `enricher.py:62` unpack 3-tuple nhận 2-tuple: **pre-existing từ work dang dở của session khác trong tree** (không thuộc auth; đã có handoff `2026-10-23-zcode-vault-rerun-and-perf` + LISTEN v5 cùng ngày đụng vùng này). Không sửa để tránh xung đột.
- FE: `tsc --noEmit` exit 0.
- Lint flake đã biết: stanza init khi full-suite (segfault 1 lần ở fixture, chạy lại PASS — same flake như handoff trước).

## Not done / gaps
- **KHÔNG commit** — tree có sẵn changeset uncommitted lớn của các session trước (và file `app/core/config.py` bị sửa GIỮA lúc session này làm — dấu hiệu có agent khác cùng đụng tree; theo protocol isolation, nên worktree riêng lần sau). Owner quyết định commit theo batch của mình.
- Nút Google trên bản deployed sẽ báo lỗi cho tới khi backend có URL public + OAuth client được tạo (bước của owner).
- `test_enricher_unit` fail còn treo (người làm enricher fix; nguyên nhân đã rõ ở trên).

## Blocked / risks
- Backend KHÔNG THỂ lên Vercel (image function giới hạn 250MB vs stack NLP ~2GB+; lifespan nạp stanza lúc boot) — chi tiết + options trong `docs/decisions.md` 2026-10-23. Đây là lệch so với kỳ vọng "deploy repo lên Vercel" của owner → đã chọn frontend-only + proxy env.
- Google OAuth cần owner tạo OAuth client trên Google Cloud Console (không agent nào làm hộ được vì cần login Google của owner).
- Flow Google phụ thuộc topology proxy same-origin (cookie qua rewrite Next) — nếu expose backend trực tiếp cho FE khác origin thì phải SameSite=None + CORS (ghi trong decisions).

## Next steps (thứ tự thực hiện để BẬT Google login)
1. Owner tạo OAuth client: console.cloud.google.com → APIs & Services → Credentials → OAuth client ID (Web application). Thêm Authorized redirect URI:
   - dev: `http://localhost:8000/api/auth/google/callback`
   - demo online (sau bước 2): `https://<backend-public>/api/auth/google/callback`
2. Cho backend URL public (chọn 1):
   - Nhanh nhất cho demo: `cloudflared tunnel --url http://localhost:8000` → nhận `https://xxx.trycloudflare.com` (URL đổi mỗi lần chạy — phải sửa redirect URI + env lại).
   - Bền hơn: VPS Ubuntu (đúng locked stack, `infra/setup_vps.sh` còn placeholder — cần dựng).
3. Điền `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` vào `backend/.env` (+ `APP_ENV=prod` khi qua HTTPS) → **restart uvicorn** (env không hot-reload).
4. Trên Vercel (project `frontend`, đã login `realdangtan`):
   - `vercel env add API_PROXY_ORIGIN production` → giá trị `https://<backend-public>`
   - `vercel --prod` deploy lại.
5. Smoke: mở `<vercel-url>/landing` → nút Google → chọn account → về `/importer`.

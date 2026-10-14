# Handoff: UI polish và kiểm tra đăng ký
- Date: 2026-10-11 19:00 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (main working tree, inline — không worktree)
- Milestone: ad-hoc UI polish, title/chat/onboarding
- Status: done (chưa commit — owner review trước)

## Done
1. **#5 — register duplicate email**: KHÔNG phải bug — backend đã 409 (verify bằng regression test).
2. **#2 — title động**: root layout metadata + `usePageTitle` hook (PageHeader auto, login/register/feedback-detail gọi trực tiếp).
3. **#3 — chat panel (LÀM LẠI 2 LẦN theo feedback owner):** lần 1 tự pha token `sidebar-accent` → owner chê tương phản; lần 2 cài chat primitives build sẵn của shadcn (`message-scroller`, `message`, `bubble`, `marker`, `input-group` + dep `@shadcn/react`) và dựng lại `chat-thread.tsx` trên surface chuẩn `bg-background`: question = `Message align="end"` + `Bubble default`, RunCard = `Card` token gốc trong `Message align="start"`, error = `Bubble destructive`, composer = `InputGroup`/`InputGroupTextarea`, note = `Marker`. ScrollArea + scrollRef thủ công bỏ — `MessageScrollerProvider autoScroll` lo follow/jump. Button/input/textarea bị CLI overwrite đã khôi phục nguyên bản từ git.
4. **#4 — onboarding**: `components/onboarding/welcome-tour.tsx` — dialog 1-lần/user cho account workspace trống, mount trong `(app)/layout.tsx`.

## Evidence
- `uv run pytest -q` → **107 passed** (unit; integration deselected theo default).
- `uv run alembic upgrade head` → `alembic current` = **0018 (head)**.
- `pnpm lint` → 0 errors (2 warnings còn lại là pre-existing trong `activity-provider.tsx`).
- `pnpm test` → **50 passed** (11 files) · `pnpm exec tsc --noEmit` → sạch.
- Runtime smoke: register user tạm → `GET /importer` 200 với chat-thread mới trong graph (SSR compile OK); user tạm đã xoá khỏi DB.
- Dev servers (uvicorn + pnpm dev) chạy xuyên session, smoke 200 cả hai.

## Not done / gaps
- `/api/reports/kpis` vẫn global (KPI health pipeline — decisions 2026-10-11).
- Chưa commit; owner cần verify UI (title từng trang, chat panel, welcome tour) bằng tay.

## Blocked / risks
- Cần kiểm tra lại title ở lần tải trang đầu và trải nghiệm chat/onboarding.

## Next steps
1. Owner verify title theo trang, chat panel và welcome tour khi danh sách workspace rỗng.
2. Commit nhỏ theo convention (feat/ui), ký `Assisted-by: claude-code`.

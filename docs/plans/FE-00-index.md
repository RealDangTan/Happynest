# FE WORKSTREAM — INDEX & STATUS BOARD

> **Owner:** Session FE (build) · **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §4 · **Contract:** [`delivery-contracts.md`](delivery-contracts.md)
> **Lãnh thổ:** chỉ được viết `frontend/` + các file `FE-*` + `13–16-*` + `backend/`. Cấm đụng `UF-*`, `AGENTS.md`, file chung ngoài quy tắc append+re-read (xem [delivery-execute-plan.md](delivery-execute-plan.md) §2).
> **Quy tắc just-in-time:** plan chi tiết của từng dòng "☐ chưa có plan" được VIẾT NGAY TRƯỚC khi thực thi, theo khuôn mẫu §3 roadmap. Đánh số task trong plan theo TDD: test trước → chạy thấy fail → code tối thiểu → pass → commit.

## Bảng plan

| # | File | Phạm vi | Viết lúc | Blocked by | Status |
|---|---|---|---|---|---|
| 01 | [FE-01-init-scaffold.md](FE-01-init-scaffold.md) | Node bump check; init shadcn vào `frontend/`; proxy rewrites; TanStack Query provider; `lib/api.ts` + Vitest | ✅ đã viết | Node ≥20.18.1 | ✅ xong 2026-08-25 |
| 02 | [FE-02-auth-shell.md](FE-02-auth-shell.md) | Middleware guard; `/login`; shell Sidebar; hook `/auth/me` | ✅ đã viết | FE-01 | ✅ xong 2026-08-25 |
| 03 | [FE-03-feedback-screens.md](FE-03-feedback-screens.md) | List + filters URL params; detail + similar; import CSV dialog | ✅ đã viết (JIT 2026-08-25) | FE-02 | ☐ |
| 04 | FE-04-analysis-runs.md | Trigger run + progress polling + results table | trước khi code màn | FE-03 | ☐ |
| 05 | FE-05-hitl-review-ui.md | Queue pending; Dialog edit/AlertDialog reject; mock rõ nhãn → swap thật khi 13 xong | đầu P2 | FE-04, UF-04, plan 13 | ☐ |
| 06 | FE-06-analytics-pages.md | Clusters page (P3) → Insights + Reports + dashboard chart (P4) | đầu P3/P4 | FE-04, UF-05, plans 14–16 | ☐ |
| 07 | FE-07-polish-demo.md | `[tuỳ chọn]` dark-mode toggle, empty states tinh gọn, data demo chuẩn bị bảo vệ | đầu P5 | tất cả | ☐ |
| 08 | FE-08-auth-register-google.md *(chưa viết)* | Đăng ký email/mật khẩu (default operations) + Google OAuth (email lạ → auto-create) + logout — BE+FE | ngay trước khi thực thi P1.5 (roadmap §1) | FE-03 · GCP credentials ([guide](../google-oauth-setup.md)) | ☐ backlog |

## Quy ước bắt buộc mọi plan/code FE

- shadcn skill rules: `gap-*` không `space-y-*`; form dùng `FieldGroup`/`Field`; Empty/Skeleton/Badge thay markup tự chế; semantic colors (`bg-primary`, `text-muted-foreground`); icon qua `data-icon`; Dialog/Sheet luôn có Title.
- Add component bằng `pnpm dlx shadcn@latest add <tên>` ĐÚNG lúc cần — không `add --all`.
- Data fetch qua wrapper `lib/api.ts` (FE-01 định nghĩa) — không fetch tay rải rác.
- Filter/pagination là URL search params; mutation xong invalidate query key tương ứng.
- Mỗi task kết thúc = commit nhỏ conventional.

## Tiến độ log (append-only)

- 2026-08-25 — tạo board; FE-01/FE-02 viết đủ chi tiết (đợt 1). — claude-code
- 2026-08-25 — thực thi xong FE-01 + FE-02 (10 commit, `pnpm build` xanh, vitest 3/3). Lệch so với plan cần biết khi đọc lại plan: (1) scaffold shadcn **không có `src/`** — mọi path `src/app|src/lib|src/hooks` trong plan hiểu là `app|lib|hooks` ở root `frontend/`, alias `@/*` → `./*`; (2) template tự init `.git` con + kèm AGENTS.md riêng → đã xoá cả hai; (3) pnpm sau bump Node v24 đòi purge node_modules và chết khi không TTY → chạy với `CI=true`; (4) TaskStop shell bash không kill tiến trình node con của `next dev` trên Windows → phải `taskkill /PID … /F`, server cũ còn chiếm :3000 gây verify sai; (5) `/login` lúc verify middleware trả 404 (chưa có trang) thay vì 200 như plan ghi — hành vi middleware vẫn đúng, trang được tạo ở FE-02 T3. — claude-code

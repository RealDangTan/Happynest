# FE WORKSTREAM — INDEX & STATUS BOARD

> **Owner:** Session FE (build) · **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §4 · **Contract:** [`delivery-contracts.md`](delivery-contracts.md)
> **Lãnh thổ:** chỉ được viết `frontend/` + các file `FE-*` + `13–16-*` + `backend/`. Cấm đụng `UF-*`, `AGENTS.md`, file chung ngoài quy tắc append+re-read (xem [delivery-execute-plan.md](delivery-execute-plan.md) §2).
> **Quy tắc just-in-time:** plan chi tiết của từng dòng "☐ chưa có plan" được VIẾT NGAY TRƯỚC khi thực thi, theo khuôn mẫu §3 roadmap. Đánh số task trong plan theo TDD: test trước → chạy thấy fail → code tối thiểu → pass → commit.

## Bảng plan

| # | File | Phạm vi | Viết lúc | Blocked by | Status |
|---|---|---|---|---|---|
| 01 | [FE-01-init-scaffold.md](FE-01-init-scaffold.md) | Node bump check; init shadcn vào `frontend/`; proxy rewrites; TanStack Query provider; `lib/api.ts` + Vitest | ✅ đã viết | Node ≥20.18.1 | ☐ |
| 02 | [FE-02-auth-shell.md](FE-02-auth-shell.md) | Middleware guard; `/login`; shell Sidebar; hook `/auth/me` | ✅ đã viết | FE-01 | ☐ |
| 03 | FE-03-feedback-screens.md | List + filters URL params; detail + similar; import CSV dialog | trước khi code màn | FE-02 | ☐ |
| 04 | FE-04-analysis-runs.md | Trigger run + progress polling + results table | trước khi code màn | FE-03 | ☐ |
| 05 | FE-05-hitl-review-ui.md | Queue pending; Dialog edit/AlertDialog reject; mock rõ nhãn → swap thật khi 13 xong | đầu P2 | FE-04, UF-04, plan 13 | ☐ |
| 06 | FE-06-analytics-pages.md | Clusters page (P3) → Insights + Reports + dashboard chart (P4) | đầu P3/P4 | FE-04, UF-05, plans 14–16 | ☐ |
| 07 | FE-07-polish-demo.md | `[tuỳ chọn]` dark-mode toggle, empty states tinh gọn, data demo chuẩn bị bảo vệ | đầu P5 | tất cả | ☐ |

## Quy ước bắt buộc mọi plan/code FE

- shadcn skill rules: `gap-*` không `space-y-*`; form dùng `FieldGroup`/`Field`; Empty/Skeleton/Badge thay markup tự chế; semantic colors (`bg-primary`, `text-muted-foreground`); icon qua `data-icon`; Dialog/Sheet luôn có Title.
- Add component bằng `pnpm dlx shadcn@latest add <tên>` ĐÚNG lúc cần — không `add --all`.
- Data fetch qua wrapper `lib/api.ts` (FE-01 định nghĩa) — không fetch tay rải rác.
- Filter/pagination là URL search params; mutation xong invalidate query key tương ứng.
- Mỗi task kết thúc = commit nhỏ conventional.

## Tiến độ log (append-only)

- 2026-08-25 — tạo board; FE-01/FE-02 viết đủ chi tiết (đợt 1). — claude-code

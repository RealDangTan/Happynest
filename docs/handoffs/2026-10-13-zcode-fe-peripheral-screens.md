# Handoff: FE peripheral screens — settings/profile/workspace/help/contact/onboarding
- Date: 2026-10-13 10:15 local
- From: zcode (GLM)
- To: any
- Branch / worktree: codex/activity-center (shared working tree, NOT committed)
- Milestone: FE peripheral screens (ngoại lai) — user request, no plan file
- Status: done (uncommitted — leave commit decision to owner)

## Done
- 6 trang mới trong `(app)` shell (auth-guarded):
  - `/onboarding` — single-page tạo workspace đầu tiên: tạo xong flip sang
    trạng thái next-steps ngay tại chỗ; stage strip LISTEN/UNDERSTAND/ACT.
    Vào từ: register redirect, WelcomeTour CTA, danger-zone xoá hết workspace.
  - `/settings` — app prefs: theme, ngôn ngữ, card Data & privacy (PII boundary).
  - `/settings/workspace` — rename/re-describe (409 surfaced),
    switcher workspace, chi tiết kỹ thuật, Danger zone xoá (AlertDialog gõ tên,
    hết workspace → `/onboarding`).
  - `/profile` — identity, Sign out; "Đổi mật khẩu" disabled "Sắp có"
    (chưa có endpoint — trung thực, không fake).
  - `/help` — 3 card theo đúng stage journey, phím tắt, FAQ (native `details`,
    không thêm dependency mới).
  - `/contact` — form demo (validate client-side), có ghi chú rõ "chưa lưu backend".
- Hook `hooks/use-language.ts` — một khoá `happynest.lang` dùng chung profile
  popover + `/settings`.
- Điều hướng: profile-panel Settings giờ là Link thật (+ Workspace settings,
  Profile); left-panel gear → `/settings`, LifeBuoy → `/help` (trước là `/qna`);
  command palette có nhóm "App" (`UTILITY_SCREENS` trong `lib/navigation.ts`);
  WelcomeTour: guard `pathname === "/onboarding"` + CTA → `/onboarding`;
  register thành công → `/onboarding` (trước là `/importer`).
- Xoá `components/shell/settings-dialog.tsx` (chức năng chuyển vào
  `/settings/workspace`; tham chiếu duy nhất là left-panel).
- `docs/api-checklist.md`: cập nhật "Vị trí trên FE" cho GET/POST auth me/logout,
  POST/PATCH/DELETE products (Hard rule #10). Không endpoint mới.

## Evidence
- `npm run typecheck` — CLEAN cho toàn bộ file tôi thêm/sửa. Còn đúng 1 error
  có TRƯỚC session này, không thuộc files của tôi: `app/(app)/importer/page.tsx:117`
  TS2345 (`phaseForImport(wizardImport.data)` — data có thể undefined qua mắt
  narrow của alias `status`; file đang có ~750 dòng uncommitted diff của agent trước).
- `npx eslint` trên đúng các file tôi đụng — 0 problems.
- `npm run test` (vitest) — 11 files / 50 tests passed.
- Chưa chạy `next build` (bị chặn bởi error importer có sẵn) và chưa smoke-test
  trên dev server (cần backend + đăng nhập).

## Not done / gaps
- Không auto-redirect khi products rỗng — chủ ý, giữ luồng WelcomeTour và tránh vòng lặp redirect.
- Form `/contact` chưa có backend (ghi chú demo ngay trên UI).

## Blocked / risks
- Error TS ở `importer/page.tsx:117` sẽ chặn `next build` — fix đề xuất 1 dòng:
  đổi dòng 117 thành `phaseForImport(wizardImport.data!)` hoặc narrow qua
  `wizardImport.data` thay vì alias `status`. Thuộc milestone importer chưa
  commit — không sửa hộ theo Hard rule #7.

## Next steps
1. Owner review UI 6 trang (`npm run dev`, đăng nhập, vào từng route; cả dark mode).
2. Xử lý error importer/page.tsx:117 rồi chạy `next build` full.
3. Commit nhỏ: `feat(fe): peripheral screens — settings/profile/workspace/help/contact/onboarding`
   kèm `Assisted-by: zcode`; api-checklist đã đồng bộ trong cùng commit (Hard rule #10).
4. Nếu muốn: nút "Tạo workspace khác" ở `/onboarding` khi đã có workspace.

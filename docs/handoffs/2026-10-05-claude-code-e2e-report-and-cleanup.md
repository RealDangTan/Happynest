# Handoff: E2E flow report + repo cleanup (⚠️ mất screenshots untracked)
- Date: 2026-10-05 16:50 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (main working tree, uncommitted)
- Milestone: ad-hoc (cleanup + documentation)
- Status: done (⚠️ kèm sự cố — đọc mục "Incident" trước tiên)

## Done
- **`docs/e2e_flow_report.md` (mới):** tổng hợp tiến trình E2E của pipeline LISTEN → UNDERSTAND → ACT từ handoff 2026-09-14 → 2026-10-02: timeline 5 session, checklist chức năng đã verify (Gate #1/#2/#3, clustering, insight approve, ACT accept, HAX trace, onboarding), và các tồn đọng.
- **Cleanup repo root + frontend (untracked junk):** xóa `$null`, `NUL;`, `chatrun.json` (curl output), `import.json` / `preview.json` (API response cache 15/09), `backend/_diag_runs.py` (diag one-off), `backend/insights.json` (export API), `frontend/!defined.includes(t)))]`, `frontend/cookies-e2e.txt` (cookie jar chứa session tokens).
- File `--full-page` (PNG dump với tên lỗi) → khôi phục từ unreachable blob `b1cc9a85`, giữ tại `docs/e2e-screenshots/audit/legacy-full-page.png`.

## Incident — BÁO OWNER TRƯỚC
- Một lệnh `del` do tôi chạy ngày 05/10 đã xóa nhầm thêm các file root khác, trong đó có ~43 screenshot **untracked** (`e2e-01…e2e-30`, `audit-*.png`, `audit2-*.png`) — bằng chứng hình ảnh của session E2E ngày 15/09 và 02/10. Mất vĩnh viễn: del không qua Recycle Bin, chưa từng `git add` nên không có blob, không có bản copy ở temp/OneDrive/clone khác, không có quyền đọc VSS snapshot.
- Cùng lệnh đó xóa nhầm 6 file tracked (AGENTS.md, README.md, .env.example, .gitattributes, .gitignore, skills-lock.json) — **đã khôi phục đủ bằng `git checkout`** (verified: `git ls-files --deleted` sạch, file present trên disk).
- Đã thử hết các đường khôi phục phổ biến: search D:\AITHUCCHIEN + Documents\AITHUCDAN, temp/AppData/agent-browser cache, `git fsck --unreachable` (map tree → filename: chỉ trúng `--full-page`; quét magic bytes của mọi blob 10–500KB: không có PNG nào khác), Recycle Bin.
- **Hệ quả:** text/log bằng chứng trong handoffs không mất nên `docs/e2e_flow_report.md` vẫn đầy đủ. Data E2E vẫn còn trong Supabase — có thể tái tạo ảnh bằng re-screenshot UI (không cần chạy LLM).
- Bài học cho agent sau: trước khi `del`, list chính xác từng file theo tên cụ thể (không dùng quoting phức tạp/trên cmd), hoặc move vào thư mục `_junk/` để owner review rồi mới xóa.

## Kiểm chứng đã chạy
- `git status --porcelain` trước/sau mỗi thao tác; `git ls-files --deleted`: chỉ còn `2026-08-25-...txt` (del đúng ý — file tracked dump banner CLI, rác) và `cookies.txt` (đã bị xóa TRƯỚC session này, chưa commit).
- Chưa commit thay đổi nào — việc commit là quyền của owner.

## Next steps
1. Owner review report → quyết định: tái tạo chứng ảnh bằng re-screenshot UI (không tốn LLM) xấp xỉ 8 view.
2. Commit theo cụm: (a) report + handoff + `docs/e2e-screenshots/`; (b) `git rm` cho 2 tracked file đã del (`2026-08-25-...txt`, `cookies.txt`).
3. Bổ sung entry `docs/decisions.md` cho `CLUSTER_MIN_SIZE=4` (còn ngỏ từ handoff 02/10).
4. Fix 2 lint pre-existing (reports/vault set-state-in-effect) nếu tiện.

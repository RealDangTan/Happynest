# Handoff: Full E2E demo với mock data + UI clean-up + 3 bug fixes
- Date: 2026-10-02 11:15 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (main working tree, uncommitted)
- Milestone: FE clean-UI pass + E2E verification với docs/feedback-mock/
- Status: done (uncommitted)

## Done
### UI clean-up (taste #61: whitespace thoải mái + #71 declutter)
- Shell: `<main>` có gutter `px-4 md:px-8` + `pt-20 pb-16` (trước đây content dính sát sidebar, zero padding); sidebar/navbar rộng `w-64`/`md:left-64` (w-60 bị clip chữ "Feedback Vault").
- NEW `components/page-header.tsx` — PageHeader(title, description, actions) dùng chung; đã mount trên 11 trang (importer, dashboard, insights, clusters, reports/summary, reports, feedbacks, analysis, data-graph, vault, matrix, stakeholders). Bỏ hết eyebrow trùng lặp ("LISTEN / Importer"…) — breadcrumb navbar đã có stage context.
- Navbar declutter: bỏ nút "Feedback" (trùng Contact us trong panel) + nút account mobile trùng; search pill hẹp lại (lg:w-44, kbd chỉ hiện xl); What's new chỉ hiện lg+.
- Spacing rhythm: các section header chuẩn `text-xs uppercase tracking-wider`, gap 4→6/8, row padding px-4/5 py-3/5; vault filters nhịp đều (w-40), bảng wrap `overflow-hidden`, footer tách `border-t pt-4`; FirstRunGuide row px-5 py-5.

### Bug fixes (phát hiện khi chạy E2E)
1. Importer "Import completed" PHANTOM: StepResult render "Import completed · 0 imported · 0 failed" khi import còn ở mapping_review (status không phải importing/failed đều rơi nhánh completed). Fix: parent re-route stale phase (result→mapping/preview theo status) + StepResult guard `status !== "imported"` → view "Import still in review".
2. `useGetMapping` poll 409 chỉ 30s trong khi proposal thật mất 1-2 phút → bảng mapping hoài trống. Fix: retry tới 150×1s (~2.5 phút).
3. `useImport` poll guard thêm: terminal status thiếu row_count → poll tiếp 1.5s (chống stale zeros trên result card).

### Config
- `backend/.env`: thêm `CLUSTER_MIN_SIZE=4` (mặc định 10 → HDBSCAN 0 cụm với 121 row mock; sweep tay: mcs=4 → 2 cụm thật). LƯU Ý: đây là tuning theo dataset size, chưa có entry decisions.md — cần ghi nhận.

## Evidence — E2E lister → UNDERSTAND → ACT (tất cả qua UI thật, LLM thật)
- Import 4 file mock (google-play 35, app-store 32, facebook 32, twitter 32) qua wizard → G1 approve-all → imported 131/135 (4 row fail PII/parse ở google-play? kiểm tra report từng file).
- Analysis: các run chạy thật (screenshot e2e-07..10: progress 0→35 live), facebook 32/32, app-store 32/32, twitter 32/32, google-play 25/35 (10 row lỗi provider validate BatchClassificationOut — model stealth/space-bunny-alpha trả JSON sai, Mode-B retry vẫn fail; đây là data-quality issue của provider).
- Clustering: 2 cụm (24 + 11 members) — e2e-18.
- UNDERSTAND: 2 investigation (d8c073e0, 3cf72e21) chạy tới Gate #2 interrupt; insight "Chưa thể xác định vấn đề tăng nhanh nhất sau import" APPROVED qua UI (e2e-21..22); evidence cards render thật.
- ACT: 3 actions (engineering/operation/support) → G3 override impact 8→6 + reason → ACCEPTED (e2e-24..26); DB xác nhận: status=accepted, human_impact=6, priority 7.88→7.26.
- Screenshots full flow: e2e-01…e2e-30 (repo root, untracked).

## Not done / gaps
- Lint còn 2 lỗi CŨ (không phải của session này): reports/page.tsx:353 và vault/page.tsx:152 react-hooks/set-state-in-effect + vài unused-import warnings (data-graph, top-navbar STAGES, insights formatRelative).
- 4 feedback google-play không import được (failed rows trong report) + 10 row google-play + 0 twitter bị skip classify do provider lỗi validate — chưa re-run lại được vì select_eligible không nhặt row đã claim bởi run COMPLETED (design hiện tại); e2e_happytest script có xử lý idempotent riêng.
- vitest OOM khi browser sessions đang mở (8GB machine) — đã chốt: tắt browser rồi chạy lại 39/39 pass. Ai chạy test nhớ close agent-browser trước.
- Backend đang chạy qua wrapper scratchpad `run_be_unbuffered.py` (task s8o50lyw, port 8000) — KHÔNG phải uvicorn chuẩn; logger exception của get_run_snapshot đã có log INFO vào scratchpad be-app.log; instrumentation logging trong runner.get_run_snapshot giữ lại (hữu ích, không PII).

## Pass 2 (2026-10-06): sửa overflow bảng + dọn nốt lint
Người dùng báo "các màn có bảng bị overflow cả web". Audit 13 file có Table +
các grid 2-3 cột, sửa theo nguyên tắc: (1) cell không bao giờ ép layout giãn,
(2) cột tự do luôn có thể co (minmax(0,1fr)), (3) chuỗi không khoảng trắng phải
break được, (4) scroll ngang chỉ nằm TRONG container bảng.

- **Root fix `components/ui/table.tsx`**: bỏ `whitespace-nowrap` mặc định của
  TableHead/TableCell — đây là thủ phạm chính (mọi ô dài ép bảng tràn page).
  Giữ nowrap có chủ đích qua className ở từng ô ngày/confidence.
- **Grid containment**: reports/data-graph/stakeholders/vault đổi `1fr` →
  `minmax(0,1fr)` + `min-w-0` — cột giữa không còn bị nội dung intrinsic đẩy.
- **break-words** cho các ô nội dung dài: vault (feedback/topic), feedbacks,
  importer (preview sample + mapping sample/description + row errors),
  data-graph (feedback/topic), stakeholders (recommendation), reports +
  insights (evidence statement — JSON tool output), feedbacks/[id] (dd của
  product data/source meta grid).
- **Matrix**: clamp vị trí chip (6%–94%) + `overflow-hidden` canvas — chip
  effort/impact=10 trước đây tràn nửa chip ra ngoài khung.
- **Shell guard**: `app/(app)/layout.tsx` thêm `min-w-0 overflow-x-clip` —
  lớp chống tràn cuối cùng cho toàn app.
- **Dọn nốt 2 lint error CŨ + warnings** (cùng pattern first-run-guide):
  reports ReportEditDialog + vault FeedbackEditDialog bỏ set-state-in-effect →
  state khởi tạo từ prop + `key={id}` ở mount site; gỡ unused imports
  (data-graph: useEffect/Play/Search/Sparkles/Alert*/analysisStats, insights:
  formatRelative, reports: updateInsight, vault: useEffect, top-navbar: STAGES).
- **Kiểm chứng**: script đo `documentElement.scrollWidth vs innerWidth` trên
  9 trang × 2 viewport (1280/390) — tất cả "X vs X" = 0 overflow. Screenshot:
  docs/e2e-screenshots/fix-01…fix-07. Gates: typecheck ✓, eslint các file
  sửa ✓ (0 problems), vitest 39/39 ✓.
- Lưu ý dev: /vault từng 404 do Turbopack stale module graph sau khi edit —
  restart `npm run dev` là hết (không phải bug app).

## Next steps
1. Commit theo cụm: (a) UI clean-up + PageHeader, (b) importer bug fixes + use-imports polling, (c) runner instrumentation, (d) .env CLUSTER_MIN_SIZE + decisions.md entry.
2. Ghi decisions.md entry cho CLUSTER_MIN_SIZE=4 (context: dataset 121 row mock; rejected alternatives: giữ 10 → 0 cụm, mcs=2 → 27 cụm nhiễu).
3. Re-run clustering + evidence đủ sau khi provider ổn định hơn; hoặc lấy model tốt hơn cho demo (user-owned decision).
4. Xem xét max-width container cho viewport rộng (screenshot e2e-28b ở 2233px bị giãn full).

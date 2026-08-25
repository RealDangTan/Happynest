# Handoff: UF workstream hoàn tất — UF-01→05 specs xong trong 1 phiên

- Date: 2026-08-25 (cuối phiên)
- From: claude-code
- To: any (đặc biệt session FE `…-b5` — đã báo trực tiếp qua SendMessage)
- Branch / worktree: main (repo root — theo quy ước owner, không worktree)
- Milestone: docs/plans/UF-00-index.md (board) — cả 5 deliverable
- Status: done

## Done

- UF-01-information-architecture.md — sitemap khớp thực tế `frontend/app/`, ma trận role×screen, ánh xạ F1–F7→screen, quy ước nav + URL params (= tên query API), inventory trạng thái + map badge ngữ nghĩa.
- UF-02-specs-auth-feedback.md — login, shell, feedback list, detail+similar, dialog nhập tay + CSV; verify code BE (`routes/feedback.py`): không filter `source`, sort cứng created_at DESC, `category` = containment chính xác JSONB.
- UF-03-spec-analysis-runs.md — trigger + confirm, polling 4s chỉ khi running, run_id trên URL (`?run=`), results table; verify `routes/analysis.py` + `schemas/analysis.py`.
- UF-04-spec-hitl-review.md — queue = filter pending, approve/edit/reject tại detail, correction dialog; verify `schemas/hitl.py` (ReviewIn có `reason?`; CorrectionIn null = không đổi → không xoá nhãn về null được).
- UF-05-spec-clusters-insights-reports.md — 4 màn P3/P4 + từ điển thuật ngữ cho người không kỹ thuật; sentinel growth_ratio=9.99 hiển thị "Mới"; priority null → ẩn; dashboard tái dùng C4.

## Evidence

- 5 commit riêng từng deliverable: `29c74b6` `8f85fa7` `1b44033` `be2d788` `75d2f78` (đều ký Assisted-by: claude-code, đường dẫn tường minh — không đụng file session FE đang commit song song: `bca33a1`, `4e7ff92` của họ xen giữa, không xung đột).
- Nguồn verify là code thật, không phải tài liệu stale: enums `models/enums.py`, schemas feedback/auth/analysis/hitl/taxonomy, routes feedback/analysis.

## Not done / gaps

- Không sửa `delivery-execute-plan.md` §1 (file chung — để owner/session FE tick dòng P1/P2 theo tiến độ tổng).
- Không tạo `docs/api-notes.md` (thiếu từ plan 12) — đã ghi OQ-1, đề nghị owner chọn tạo mới hoặc đổi link sang api-checklist.md.

## Blocked / risks

- Không blocker. Lệch đáng nhớ: yêu cầu "mock DEMO" của UF-04 bỏ vì plan 13 phần BE đã thực thi xong cùng ngày (endpoints ✅ production trong api-checklist) — spec bám API thật, lý do ghi trong header UF-04.
- OPEN QUESTION OQ-1..11 gom cuối từng file UF-* (api-notes thiếu; root `/` còn placeholder; không logout; created_at picker; back-giữ-filter; không có GET list runs; snapshot config không trả về; reviewer xem raw?; xoá nhãn về null; ngưỡng trend là env; insight review_status display-only).

## Next steps

1. Owner review 5 spec (ưu tiên OQ-8 xem-raw-khi-review và OQ-1 api-notes).
2. Session FE: viết FE-04 dựa UF-03; FE-05 dựa UF-04 (đã đủ điều kiện); FE-06 phần clusters chờ P3 mount nhưng UF-05 đã sẵn sàng sớm.
3. Việc nhỏ gợi ý gộp vào FE-04 hoặc FE-07: redirect root `/` → `/dashboard` (OQ-3).

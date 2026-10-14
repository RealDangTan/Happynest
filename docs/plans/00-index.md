# PLANS — ACTIVE BOARD

> Cập nhật 2026-10-14. Plan hoàn tất đã được xóa khỏi thư mục; xem [tóm tắt trạng thái](../plan_report.md), [decision log](../decisions.md) và [handoffs](../handoffs/). Bản gốc vẫn nằm trong Git history.
> Quy tắc: lệch kế hoạch → entry dated trong decisions; không Docker, không subagent, giữ PII boundary và đồng bộ API checklist.

## Không còn plan đang mở

Plan 33 đã chạy ngày 2026-10-09 qua endpoint System One tương thích TypeSafe trên OpenRouter: **FAIL** vì accuracy/calibration; p95 1.0607 s và 0 unrecovered 429. Xem [báo cáo S7](../s7-jev-evaluation.md). Plan đã đóng và được xóa theo yêu cầu dọn docs; bản gốc còn trong Git history.

Quyết định 2026-10-08 dùng `typesafe/jev-router` qua OpenRouter đã bỏ điều kiện tích hợp 34B. S7 không thay model production; Jev System One và Jev Router là hai đường khác nhau.

## Đã đóng

Series 01–32, 34, FE-01–14, UF và delivery đã hoàn tất hoặc được thay thế; ACT best practices (35) đã hoàn tất tại `ea6535c`. Tóm tắt, bằng chứng và phần việc ngoài plans nằm trong [plan_report.md](../plan_report.md).

## Thay đổi theo yêu cầu owner — 2026-10-14

| Plan | Trạng thái | Kết quả |
|---|---|---|
| [37-shared-workspace.md](37-shared-workspace.md) | Hoàn tất | Mọi tài khoản đăng nhập dùng chung workspace và toàn bộ thao tác. Hợp đồng, kiểm thử và schema đã đồng bộ; xem handoff 2026-10-14. |

Tài liệu triển khai đã đồng bộ ngày 2026-10-14; coding agent bắt đầu từ [docs/README.md](../README.md). Phạm vi lượt cập nhật này nằm ngoài `docs/thesis/`.

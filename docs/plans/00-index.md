# PLANS — ACTIVE BOARD

> Cập nhật 2026-10-09. Plan hoàn tất đã được xóa khỏi thư mục; xem [tóm tắt trạng thái](../plan_report.md), [decision log](../decisions.md) và [handoffs](../handoffs/). Bản gốc vẫn nằm trong Git history.
> Quy tắc: lệch kế hoạch → entry dated trong decisions; không Docker, không subagent, giữ PII boundary và đồng bộ API checklist.

## Nghiên cứu tùy chọn chưa hoàn tất

| # | File | Phạm vi | Trạng thái |
|---|---|---|---|
| 33 | [33-spike-s7-jev.md](33-spike-s7-jev.md) | Benchmark trực tiếp TypeSafe/Jev với baseline enricher v3 | Script đã có (`168b3b4`); chưa chạy, chờ key. Không chặn delivery |

Quyết định 2026-10-08 dùng `typesafe/jev-router` qua OpenRouter đã bỏ điều kiện tích hợp 34B. Không coi spike S7 là PASS khi chưa có số đo.

## Đã đóng

Series 01–32, 34, FE-01–14, UF và delivery đã hoàn tất hoặc được thay thế; ACT best practices (35) đã hoàn tất tại `ea6535c`. Tóm tắt, bằng chứng và phần việc ngoài plans nằm trong [plan_report.md](../plan_report.md).

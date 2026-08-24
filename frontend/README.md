# frontend — placeholder (phase B1)

Giai đoạn backend foundation (12 phase, hoàn thành 2026-08-25) KHÔNG bao gồm UI.
Thư mục này giữ chỗ cho giai đoạn kế tiếp: dashboard PM/operations —
danh sách feedback + filter, badge `requires_human_review`, xem tiến độ
analysis run, màn hình HITL review/correction.

API backend sẵn sàng cho UI: xem [`../docs/api-notes.md`](../docs/api-notes.md).
Auth từ browser đi qua cookie httpOnly `access_token` (đã thiết kế từ Phase 04);
CORS whitelist bằng env `CORS_ORIGINS`.

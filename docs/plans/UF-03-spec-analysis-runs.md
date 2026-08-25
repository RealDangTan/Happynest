# UF-03 — Screen spec: Analysis (trigger · progress polling · results)

> **Phiên bản:** v1.0 · **Ngày:** 2026-08-25
> **Nguồn bám:** plan 09 (endpoint đã ship ✅) · verify code `backend/app/api/routes/analysis.py` + `schemas/analysis.py` 2026-08-25 · contract C5/C6 là pha sau (clusters/insights — KHÔNG nằm trong màn này) · quy ước chung [UF-01](UF-01-information-architecture.md)
> **Ghi chú:** đây là màn P1 cuối (FE-04 viết sau spec này). Flow F4/F5: classify + embed hàng loạt chạy nền.

---

## Màn — Analysis

- **Route / Roles / Pha:** `/analysis` · pm | operations · P1 (FE-04; trang placeholder hiện tại thay bằng màn này)
- **Purpose:** kích hoạt batch phân loại cho các feedback chưa xử lý, theo dõi tiến độ, xem kết quả từng item; cũng là nơi "hồi sinh" các row bị bỏ lại khi run cũ crash/fail.
- **Data (verify code, KHÔNG phát minh):**
  | Endpoint | Shape |
  |---|---|
  | `POST /api/analysis/runs` → **201** | `{run_id}` ngay lập tức; job nền bắt đầu sau khi response gửi. Idempotent: chỉ nhặt `analysis_run_id IS NULL` |
  | `GET /api/analysis/runs/{run_id}` | `{id, status: running\|completed\|failed, processed_count, total_count, error\|null, started_at, completed_at\|null}` |
  | `GET /api/analysis/runs/{run_id}/results?limit&offset` | Envelope `{total, limit, offset, items[FeedbackOut]}` — chỉ feedback thuộc run; item chưa xử lý xong có nhãn `null` |
  - **Không có endpoint liệt kê runs** và **không có endpoint đếm row chưa xử lý** → hệ quả UX bắt buộc ở dưới.
- **Components:** Card · AlertDialog (confirm trigger) · Progress · Table · Badge · Skeleton · Empty · Button · sonner toast.
- **Bố cục đề xuất (3 khối dọc):**
  1. **Khối trigger** — mô tả 1 dòng ("Phân loại + tạo embedding cho mọi feedback chưa xử lý; tốn LLM credit") + nút "Chạy phân loại" → mở AlertDialog confirm (vì tốn tiền): "Chạy trên toàn bộ feedback chưa xử lý?" → Confirm → POST → ghi `run_id` lên URL `?run=<uuid>` ngay.
  2. **Khối progress** (chỉ hiện khi có `?run=`): tiêu đề run rút gọn + Progress bar `%` = processed/total + text "x/y đã xử lý" + Badge trạng thái. Khi `status != running`: ngừng poll, hiện kết quả tổng (completed: toast xanh; failed: Alert destructive kèm `error`).
  3. **Khối results** — Table của run hiện tại: cột như list Feedbacks (UF-02 Màn 3, đã gồm flag `requires_human_review`) + thêm cột `confidence` (%); item nhãn `null` → ô nhãn hiển thị "…đang xử lý". Row click → detail. Phân trang offset như list.
- **States:**
  - **Loading:** progress block Skeleton trong lúc poll đầu tiên; results skeleton dòng.
  - **Empty (chưa có `?run=`):** Empty giải thích mục đích màn + CTA chính là nút trigger. Đây là landing mặc định của `/analysis`.
  - **Trigger khi không còn gì để xử lý:** POST vẫn 201 với `total_count=0`, run hoàn tất tức thì → thông báo info (toast hoặc Alert): "Không có feedback mới nào cần xử lý."
  - **Failed:** Alert destructive hiển thị `error` (tóm tắt từ server) + nút phụ **"Chạy lại phần còn lại"** = POST lần nữa (an toàn: chỉ row chưa claim được nhặt — cơ chế crash-safe của runner).
  - **Polling:** TanStack Query `refetchInterval` ~4s khi `status === "running"`, trả `false` (ngừng poll) khi completed/failed. Không tự refresh trang.
- **Edge cases:**
  - Refresh giữa chừng: trạng thái sống nhờ `?run=` trên URL — share link được.
  - Người khác (tab/session khác) cũng trigger: tạo thêm run riêng, không phá run hiện tại; hai run cùng lúc chỉ làm việc không trùng nhau (claim theo row). UI không cần chặn, nhưng nút trigger **disable khi run đang theo dõi ở trạng thái running** (quy tắc spec §4).
  - Run dài (dataset lớn: ~1–2s/item do LLM) — progress tăng từ từ là bình thường; KHÔNG hiện đếm giờ ước tính (dễ sai).
  - Item lỗi đơn lẻ bị bỏ qua trong run (không retry trong run) — thấy ở results là row nhãn vẫn `null` khi run completed → hướng dẫn dùng "Chạy lại phần còn lại".
  - **Backend chết/restart giữa lúc đang poll** (kịch bản evidence checkpoint của luận văn): request poll lỗi mạng → giữ nguyên progress cuối cùng đã thấy + toast lỗi mạng chung; KHÔNG xoá khối progress, KHÔNG đổi URL. Khi backend lên lại, polling tự tiếp tục và progress chạy tiếp từ giá trị thật của server — UI không cần làm gì ngoài retry mặc định của TanStack Query.
- **Acceptance criteria:**
  - [ ] Trigger → URL đổi thành `/analysis?run=<uuid>` NGAY khi nhận `{run_id}`; refresh giữ nguyên tiến độ.
  - [ ] Polling dừng hẳn khi completed/failed (network tab: không request nữa).
  - [ ] Trigger 2 lần liên tiếp khi đang running: nút bị disable sau lần 1.
  - [ ] Run fail giữa chừng (tắt backend) → sau khi restart backend, bấm "Chạy lại phần còn lại" → run mới nhặt đúng các row còn thiếu, không nhân đôi kết quả (soi tổng call LLM qua `llm_call_logs` nếu muốn bằng chứng).
  - [ ] Results item chưa xử lý hiển thị placeholder "…đang xử lý", không hiện "null".

## Rủi ro UX & câu hỏi mở

> **Trạng thái 2026-08-26:** OQ-6/7 đã chốt với owner (decisions.md cùng ngày).

- **OQ-6 — ✅ resolved:** chấp nhận v1, KHÔNG thêm GET list runs — run_id sống trên URL + toast; mất URL là không tra cứu được (chấp nhận có chủ đích).
- **OQ-7 — ✅ resolved:** BE sẽ bổ sung 4 field snapshot (`llm_model`, `prompt_version`, `pipeline_version`, `embedding_model`) vào RunProgressOut — backward-compatible; UI hiển thị 1 dòng metadata nhỏ dưới progress bar ("Run dùng model X · prompt vY"). Việc BE thuộc session FE/BE, sync api-checklist khi làm; UI chỉ hiện KHI field có mặt (feature-detect, không lỗi nếu chưa ship).
- **Rủi ro chi phí:** double-click/nhiều tab trigger nhiều run → nhiều call LLM song song. Đã giảm nhẹ bằng confirm dialog + disable; chấp nhận residual risk vì dataset ≤1500 và người dùng nội bộ.
- **Rủi ro hiểu nhầm:** "Chạy lại phần còn lại" tạo run MỚI chứ không resume run cũ (URL `?run=` đổi) — copy nút phải nói đúng điều đó ("Chạy lại" thay vì "Tiếp tục").

# UF-04 — Screen specs: HITL review (queue · approve/edit/reject · corrections)

> **Phiên bản:** v1.0 · **Ngày:** 2026-08-25
> **Nguồn bám:** contract [`delivery-contracts.md`](delivery-contracts.md) C3 · [`../user-flows.md`](../user-flows.md) F6 · verify code `backend/app/api/routes/` + `schemas/hitl.py` + plan `13-hitl-langgraph.md` 2026-08-25 · quy ước chung [UF-01](UF-01-information-architecture.md)
> **Lệch so với board (ghi rõ):** board yêu cầu spec **mock "DEMO"** trước khi plan 13 thật — mục này **hết hiệu lực**: phần BE của plan 13 đã thực thi xong 2026-08-25 (graph + routes + integration xanh, evidence script `backend/scripts/evidence_hitl_checkpoint_resume.py`), `/reviews` + `/corrections` đã ✅ production trong [`../api-checklist.md`](../api-checklist.md). Spec bám API THẬT, không cần chế độ mock.
> **Ghi chú limitation bắt buộc (theo board):** hệ thống **không có logout** — cookie hết hạn theo tuổi thọ token (~12h); nêu rõ trong kịch bản demo (xem OQ-2 UF-01).

---

## Màn 1 — Queue chờ duyệt

- **Route / Roles / Pha:** `/feedbacks?review_status=pending` (dùng lại màn list — KHÔNG tạo route mới) · pm | operations · P2 (FE-05; điều kiện: spec này + plan 13)
- **Purpose:** hàng đợi mọi feedback runner đánh dấu `review_status='pending'` (do `requires_human_review`: critical / safety / PII / confidence thấp) để con người duyệt nội dung.
- **Data:** `GET /api/feedbacks?review_status=pending&limit&offset` → envelope chuẩn `{total, limit, offset, items[FeedbackOut]}`. Số lượng queue = `total` của request này (hiển thị "n mục chờ duyệt").
- **Components:** tái dùng toàn bộ màn list (UF-02 Màn 3) + 1 nút/shortcut "Chờ duyệt" trên header trang feedbacks (link gắn sẵn filter) — người vận hành vào queue trong 1 click.
- **States:** như list; **empty queue là trạng thái tốt** → Empty tích cực: "Không có mục nào chờ duyệt." + CTA phụ "Xem tất cả phản hồi" (xoá filter).
- **Luồng ra quyết định:** click row → detail `/feedbacks/[id]` — nơi chứa 3 hành động (Màn 2). Không đặt nút hành động ngay trên row của bảng (tránh duyệt bừa khi chưa đọc nội dung).
- **Acceptance criteria:**
  - [ ] Vào queue bằng URL share được (filter nằm trên URL — quy tắc UF-01 §4).
  - [ ] Duyệt xong 1 mục (ở Màn 2) rồi quay lại queue → mục đó biến mất, `total` giảm (nhờ invalidate).

## Màn 2 — Hành động review (tại detail)

- **Route / Roles / Pha:** `/feedbacks/[id]` · pm | operations · P2 (FE-05)
- **Purpose:** phê duyệt NỘI DUNG một feedback pending — quyết định văn bản sau sanitize đủ tin cậy làm dữ liệu nền cho phân tích.
- **Data:** `POST /api/reviews/{feedback_id}`:
  ```jsonc
  // Request — ReviewIn (verify schemas/hitl.py):
  { "action": "approve" | "edit" | "reject",
    "edited_content": "…",   // BẮT BUỘC khi action=edit (rỗng → 422)
    "reason": "…" }          // tuỳ chọn (API hỗ trợ; UI dùng cho edit/reject)
  // 200 → FeedbackOut với review_status mới: approved | edited | rejected
  ```
  Side effect server: `edited_content` chạy lại Presidio trước khi lưu thành `sanitized_content`; `edit`/`reject` tự ghi `correction_examples`.
- **Bố cục:** thanh hành động trên detail, CHỈ hiện khi `review_status === "pending"`: `[Duyệt]` (primary) · `[Sửa nội dung]` (outline) · `[Từ chối]` (destructive outline).
- **Ba luồng:**
  1. **Duyệt** — 1 click → toast "Đã duyệt." Không dialog (ưu tiên tốc độ; approve là lựa chọn an toàn nhất).
  2. **Sửa nội dung** — Dialog: Textarea **prefill bằng `sanitized_content` hiện tại** + Field `reason` (tuỳ chọn, placeholder "Vì sao phải sửa"). Client chặn submit khi textarea rỗng/chỉ khoảng trắng (đúng rule 422 của server). Confirm → POST `action="edit"`.
  3. **Từ chối** — AlertDialog destructive: giải thích hậu quả (mục bị đánh dấu rejected, không tham gia phân tích) + Field `reason` khuyến khích nhập → POST `action="reject"`.
- **Sau thành công (cả 3 luồng):** invalidate query key list + detail → badge `review_status` cập nhật, thanh hành động biến mất; toast ngắn. Nếu người dùng đến từ queue và còn item pending kế tiếp trong trang vừa xem → offer điều hướng sang item kế ("Xem mục chờ duyệt tiếp theo" — link/toast action) để duyệt tuần tự mượt khi demo.
- **States & lỗi:**
  | Tình huống | UI |
  |---|---|
  | Item đã bị người/tab khác duyệt (**409**) | Alert "Mục này đã được xử lý trước đó." + tự invalidate để thấy trạng thái mới |
  | Edit thiếu nội dung (client chặn trước) | validation inline dưới textarea |
  | 404 | Empty "Không tìm thấy" + về queue |
  | Mutation loading | cả 3 nút disable đồng thời (chống double-submit) |
- **Edge cases:**
  - **Không có undo review**: sau approve/edit/reject không API nào đưa về pending → copy confirm của reject/edit phải nói rõ "thao tác không hoàn tác".
  - Người review chỉ làm việc trên **text đã sanitize** — PII gốc (email/SĐT…) đã bị che thành `<EMAIL_ADDRESS>`… Đây là chủ đích (PII boundary), không phải bug; hướng dẫn người demo trước.
  - Graph LangGraph chạy ngầm sau POST (interrupt/resume + checkpoint Postgres) — UI không cần xử lý gì đặc biệt; crash backend giữa chừng → resume tự lo phía BE, FE chỉ cần retry POST bình thường.
- **Acceptance criteria:**
  - [ ] Approve/edit/reject mỗi luồng trả đúng `review_status` mới trên UI ngay mà không F5.
  - [ ] Edit với textarea rỗng không thể submit; cố tình gọi thẳng API → 422 được hiển thị đúng inventory.
  - [ ] POST lại 1 mục đã duyệt → thấy Alert 409 "đã được xử lý", không crash.
  - [ ] `edited_content` chứa email/SDT giả lập → sau lưu, detail hiển thị bản ĐÃ che PII (Presidio chạy lại) chứ không giữ nguyên text gõ vào.

## Màn 3 — Sửa nhãn (correction)

- **Route / Roles / Pha:** Dialog tại `/feedbacks/[id]` · pm | operations · P2 (FE-05)
- **Purpose:** sửa NHÃN AI (không đụng nội dung) khi con người thấy máy phân loại sai; mỗi lần sửa nuôi `correction_examples` → few-shot cho classifier về sau (vòng lặp cải tiến F6).
- **Data:** `POST /api/corrections/{feedback_id}`:
  ```jsonc
  // Request — CorrectionIn: CHỈ field được gửi (khác null) mới được cập nhật;
  // rỗng toàn bộ → 422. Enum lạ → 422. Phần tử categories rỗng → 422.
  { "categories": ["hallucination", …], "ai_issue": "…|null?", "severity": "…",
    "sentiment": "…", "note": "…" }
  // 200 → CorrectionOut = FeedbackOut cập nhật + "correction_recorded": true
  ```
  Áp dụng cho **mọi feedback đã classify** (`categories` khác null), bất kể `review_status`; chưa classify → **409**.
- **Bố cục:** nút "Sửa nhãn" trên detail (ẩn khi chưa classify) → Dialog form:
  - `categories`: chip editor — gợi ý giá trị lấy từ các category đã xuất hiện trong dữ liệu đang có (client nhớ từ những list đã load); cho phép gõ giá trị mới (BE chấp nhận chuỗi tự do, chỉ chặn rỗng).
  - `ai_issue`: Select 7 giá trị enum + "— giữ nguyên —".
  - `severity` / `sentiment`: Select enum tương ứng + "— giữ nguyên —".
  - `note`: Textarea tuỳ chọn ("vì sao sửa") → ghi vào `human_reviews.reason` phía BE.
  - Nút Lưu disable đến khi ≥ 1 field khác "giữ nguyên".
- **Sau thành công:** invalidate list + detail; toast "Đã ghi nhận chỉnh sửa — sẽ giúp phân loại sau chính xác hơn."
- **States & lỗi:** 409 chưa classify → Alert hướng dẫn chạy analysis trước; 422 body rỗng khó xảy ra (client chặn) nhưng vẫn map inventory; loading disable nút.
- **Edge cases:**
  - **Không thể xoá nhãn về null** — API hiểu `null` = "không đổi" (OQ-9). UI chỉ cho thay giá trị, không cho "bỏ trống lại".
  - Correction KHÔNG đổi `review_status` — một mục rejected vẫn sửa nhãn được (hợp lệ theo contract).
- **Acceptance criteria:**
  - [ ] Sửa severity low → critical: detail cập nhật badge ngay; DB có dòng `correction_examples` mới (check query hoặc qua hành vi few-shot sau này).
  - [ ] Mở form rồi bấm Lưu ngay không đổi gì → nút disable, không gọi API.
  - [ ] Feedback chưa classify (labels null) không thấy nút "Sửa nhãn".

---

## Rủi ro UX & câu hỏi mở

- **OQ-8 — Có cho reviewer xem `raw_content` khi duyệt?** Thiết kế §4 của delivery-design-spec cho phép "raw content chỉ hiện qua toggle explicit", nhưng FE-03 đã chốt chặt hơn: UI không bao giờ gọi `include_raw=true`. Với HITL, xem raw giúp đánh giá sanitizer có làm mất nghĩa không — nhưng mở lại rủi ro PII lên màn hình (screen-share lúc demo!). **Đề xuất:** giữ chặn tuyệt đối trong v1; owner quyết nếu muốn mở toggle chỉ cho role operations, phải qua decisions.md TRƯỚC.
- **OQ-9 — Không xoá nhãn được về null** (CorrectionIn: null = không đổi): nếu phát sinh nhu cầu "AI gán nhãn oan, muốn bỏ hẳn" → cần BE bổ sung sentinel/cơ chế riêng → decisions.md. v1 chấp nhận chỉ thay thế.
- **Rủi ro demo:** duyệt nhầm do đọc nhanh — giảm nhẹ bằng cách bắt reject/edit qua dialog có nội dung context, approve là 1-click có chủ đích; không có bulk-action (cố ý, tránh duyệt hàng loạt vô trách nhiệm trong v1).
- **Rủi ro hiểu nhầm trạng thái:** `edited` ≠ thất bại — nó là kết quả tích cực (người dùng cải thiện dữ liệu); màu badge amber dễ bị đọc là cảnh báo. FE cân nhắc tone màu trung tính-tích cực cho `edited` theo map UF-01 §5.

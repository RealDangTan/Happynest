# UF-02 — Screen specs: Login · Shell · Feedback list · Detail (+similar) · Nhập liệu/CSV

> **Phiên bản:** v1.0 · **Ngày:** 2026-08-25
> **Nguồn bám:** contract [`delivery-contracts.md`](delivery-contracts.md) (feedback endpoints đã ship) · [`../user-flows.md`](../user-flows.md) F1–F3/F5 · [`../api-checklist.md`](../api-checklist.md) · quy ước chung [UF-01](UF-01-information-architecture.md) §4–§5
> **Verify API 2026-08-25:** `backend/app/api/routes/feedback.py` + `schemas/feedback.py` + `models/enums.py`. **KHÔNG có filter `source`; KHÔNG có sort param** (sort cứng `created_at DESC, id DESC`); `category` = match chính xác 1 giá trị nằm trong JSONB `categories`.
> **Ghi chú hiện trạng:** cả 5 màn đều đã ship theo FE-02/FE-03 (detail + similar xong 2026-08-25, commit `9f60c3b`) — spec này là chuẩn tham chiếu + acceptance checklist.

---

## Màn 1 — Login

- **Route / Roles / Pha:** `/login` · public · P1 ✅ (FE-02)
- **Purpose:** đăng nhập bằng tài khoản seed; cấp cookie httpOnly làm phiên cho toàn app.
- **Data:** `POST /api/auth/token` — body `application/x-www-form-urlencoded` (`username`=email, `password`) → `Set-Cookie access_token` (httpOnly, SameSite=Lax) + body `{access_token, token_type:"bearer"}`. Sai → **401 thông điệp chung** (chống dò email).
- **Components:** Card · Field/Input · Button · Alert.
- **States:**
  - Loading: nút disable, không cho submit lần 2.
  - Error 401: Alert destructive trong card — "Email hoặc mật khẩu không đúng." Không tiết lộ email có tồn tại hay không.
  - Success: redirect `/dashboard` (mặc định) hoặc về trang định đi trước nếu app lưu được; cookie do server set, FE không đụng token.
- **Edge cases:**
  - Đã đăng nhập mà mở `/login`: gọi `/auth/me` thành công → redirect `/dashboard` (tránh đăng nhập lại vô ích).
  - Backend chưa chạy → fetch fail: toast lỗi mạng chung (inventory UF-01 §5), giữ nguyên form.
- **Acceptance criteria:**
  - [ ] Sai mật khẩu → đúng 1 Alert chung, không phân biệt "email không tồn tại".
  - [ ] Đăng nhập xong F5 refresh vẫn còn phiên (cookie sống qua reload).
  - [ ] Không lưu password/token ở bất kỳ đâu phía client (localStorage/sessionStorage sạch).

## Màn 2 — Shell & Sidebar

- **Route / Roles / Pha:** `(app)/layout.tsx` · pm | operations · P1 ✅ (FE-02)
- **Purpose:** khung điều hướng 6 mục + guard + nhận diện user; mọi màn nghiệp vụ render bên trong.
- **Data:** `GET /api/auth/me` → `{id, email, role}` (hook `useMe`, cache TanStack Query).
- **Components:** Sidebar (+SidebarMenu/Button) · Avatar · DropdownMenu · Badge (`variant=secondary`) · Separator.
- **States:**
  - `me` loading: khung sidebar render sẵn, vùng user là Skeleton nhỏ.
  - `me` 401: middleware/handler đưa về `/login` (không render shell nửa vời).
  - Nav active: mục route hiện tại highlight (`data-active`).
- **Edge cases:**
  - **Không logout** — non-goal v1 (contract): menu avatar chỉ hiển thị email + badge role. Ghi chú limitation vào kịch bản demo (OQ-2 UF-01).
  - Role hiển thị giá trị enum thô (`pm` / `operations`) — chấp nhận, không cần nhãn tiếng Việt đẹp.
- **Acceptance criteria:**
  - [ ] 6 mục nav đúng thứ tự UF-01 §4, active state đúng khi điều hướng.
  - [ ] Xoá cookie rồi refetch bất kỳ trang `(app)` → về `/login`, không crash.

## Màn 3 — Feedback list

- **Route / Roles / Pha:** `/feedbacks` · pm | operations · P1 ✅ (FE-03)
- **Purpose:** duyệt/lọc toàn bộ feedback; đồng thời là **cửa vào queue HITL** qua filter `review_status=pending` (UF-04).
- **Data:** `GET /api/feedbacks?limit(≤100, def20)&offset&review_status&severity&category` → `{total, limit, offset, items[FeedbackOut]}`. FeedbackOut gồm: id, source, external_ref|null, created_at, imported_at, review_status, pii_detected, severity|null, categories[]|null, ai_issue|null, sentiment|null, confidence|null, requires_human_review, sanitized_content|null.
- **Bố cục:** thanh filter trên cùng + Table + pagination dưới đáy.
  - Filter: Select `review_status` (5 enum + tất cả) · Select `severity` (4 + tất cả) · Input `category` (text, match chính xác 1 giá trị trong mảng). Nút phụ "Xoá bộ lọc" khi đang có filter.
  - Cột đề xuất: `created_at` (định dạng ngắn) · `source` · snippet `sanitized_content` (1–2 dòng, truncate) · Badge severity · Badge sentiment · chips categories (tối đa 2 + "+n") · Badge review_status · icon/badge `pii_detected` · dấu hiệu `requires_human_review` (icon alert nhỏ). Row click → `/feedbacks/[id]`.
  - Pagination: prev/next + text "đang xem x–y trên total"; không cho chỉnh limit trên UI (mặc định 20).
- **Components:** Table · Select · Input · Badge · Skeleton · Empty · Button; component pagination thêm bằng `pnpm dlx shadcn@latest add pagination` lúc cần.
- **States:**
  - Loading: skeleton đúng số dòng cấu hình, header table đứng yên.
  - Empty DB (chưa import gì): Empty + CTA mở dialog nhập liệu (Màn 5).
  - Empty vì filter: Empty + nút "Xoá bộ lọc" (clear params, giữ offset=0).
  - URL param sai giá trị (vd `severity=hacker`): bỏ param đó, dùng mặc định — không lỗi trắng trang.
- **Edge cases:** không filter `source` (API không có); không sort tùy chọn (server cứng created_at DESC); không sửa/xoá row (không endpoint); hàng chưa qua pipeline → snippet trống + badge "chưa xử lý".
- **Acceptance criteria:**
  - [ ] Mọi filter/pagination nằm trên URL đúng tên query API; đổi filter → offset về 0.
  - [ ] Copy link có filter → tab khác (đã login) thấy cùng bảng.
  - [ ] `category=giao tiếp` chỉ khớp feedback có CHÍNH XÁC giá trị đó trong `categories` (containment), không phải search con-chuỗi.

## Màn 4 — Detail + Similar

- **Route / Roles / Pha:** `/feedbacks/[id]` · pm | operations · P1 🔨 (FE-03 đang build)
- **Purpose:** xem đầy đủ 1 bản ghi đã sanitize + nhãn AI; so sánh với các feedback tương tự về ngữ nghĩa (F5).
- **Data:**
  - `GET /api/feedbacks/{id}` → FeedbackOut. **UI tuyệt đối không gọi `include_raw=true`** — raw_content không bao giờ lên UI (PII hard rule AGENTS #2).
  - `GET /api/feedbacks/{id}/similar?k=5` (k 1–50) → `[{id, score, source, snippet}]` — snippet cắt từ sanitized_content. Row chưa embed → **409** kèm hướng dẫn chạy analysis trước.
- **Bố cục:**
  - Header: nút back (về `/feedbacks`, giữ filter đang có nếu tiện) + id rút gọn (mono) + badges tổng quan.
  - Card nội dung: metadata (source · external_ref nếu có · created_at · imported_at) · blockquote `sanitized_content` · Badge severity/sentiment/PII/review_status.
  - Tabs: **Nhãn AI** (categories chips · ai_issue · confidence % · rationale nếu có · flag requires_human_review) | **Similar** (list: score dạng %, source, snippet; click → sang detail khác).
- **Components:** Card · Tabs · Badge · Separator · Skeleton · Empty · Button.
- **States:** loading = skeleton card; 404 = Empty "Không tìm thấy feedback" + link về list; similar 409 = Alert destructive với hướng dẫn hành động ("Chạy analysis để tạo embedding") nhưng **phần còn lại của trang vẫn hiện bình thường**.
- **Edge cases:** `sanitized_content` null (chưa chạy pipeline) → placeholder giải thích + gợi ý chạy analysis; similar list < k → hiện ít hơn, không lỗi; confidence null → ẩn dòng thay vì hiện "null%".
- **Acceptance criteria:**
  - [ ] Grep toàn bộ code FE không có chuỗi `include_raw=true`.
  - [ ] Feedback chưa embed: trang detail vẫn dùng được, riêng tab Similar báo 409 đúng nội dung hướng dẫn.
  - [ ] Click 1 item similar → detail mới load, không mất khả năng back.

## Màn 5 — Nhập liệu đơn lẻ + Import CSV (dialog)

- **Route / Roles / Pha:** component `data-entry-dialog.tsx` tại `/feedbacks` (không route riêng) · pm | operations · P1 ✅ (FE-03)
- **Purpose:** 2 đường ingestion của F2 ngay trong UI: thêm 1 feedback thủ công hoặc import loạt CSV.
- **Data:**
  - Tab nhập tay: `POST /api/feedbacks` `{source*, content*, external_ref?, created_at?}` → **201** FeedbackOut.
  - Tab CSV: `POST /api/feedbacks/import-csv` multipart file `.csv` → `200 {imported, failed, errors:[{row, reason}]}` — lỗi từng dòng KHÔNG abort file; backend đọc utf-8-sig (CSV Excel BOM OK). Cột bắt buộc `source`, `content`; tuỳ chọn `created_at` ISO 8601, `external_ref`.
- **UX flow:**
  - Nút "Nhập liệu" trên list → Dialog có Tabs `[Nhập tay | Import CSV]` (Tabs luôn kèm Title — rule shadcn).
  - Nhập tay: Field bắt buộc source (Input), content (Textarea); tuỳ chọn external_ref, created_at (để trống = thời điểm ingest). Submit → toast success + invalidate query key list + đóng dialog.
  - CSV: chọn file (client check đuôi `.csv` trước khi upload) → upload → panel kết quả: Alert tổng (`imported`/`failed`) + bảng errors (`row`, `reason`) khi `failed > 0`. Import thành công một phần vẫn là kết quả bình thường — không coi là error toast.
- **Components:** Dialog · Tabs · FieldGroup/Field · Input · Textarea · Button · Progress (file lớn) · Alert · Table (errors) · sonner toast.
- **States:** validation inline 422 dưới từng field; 422 "File phải có đuôi .csv" từ server → Alert trong dialog; loading = nút disable.
- **Edge cases:** sau ingest thô feedback **chưa có nhãn** — phải chạy analysis (UF-03) mới classify/embed; UI nên nói rõ điều đó ở toast ("Đã thêm — chạy Analysis để phân loại"). Không có sửa/xoá sau import — chỉnh nhãn sau này bằng correction (UF-04).
- **Acceptance criteria:**
  - [ ] Import CSV 10 dòng trong đó 2 dòng thiếu `content` → report `imported=8, failed=2`, 8 dòng mới xuất hiện ở list sau invalidate.
  - [ ] Chọn file `.xlsx` → bị chặn client-side, không gọi API.
  - [ ] created_at người dùng tự điền được hiển thị đúng ở list/detail (event time ≠ imported_at).

---

## Rủi ro UX & câu hỏi mở

- **OQ-4 — `created_at` nhập tay:** để datetime-local picker hay ô text ISO? Picker thân thiện hơn nhưng thêm component (`pnpm dlx shadcn add calendar popover` nếu dùng DatePicker đầy đủ — cân nhắc chi phí); đề xuất mặc định: để trống (server lấy now), ô text ISO cho trường hợp dữ liệu lịch sử.
- **OQ-5 — Back từ detail "giữ filter":** muốn giữ đúng bộ lọc cũ cần đọc params từ URL trước khi điều hướng (state không tự giữ). Ưu tiên thấp — chấp nhận back = list mặc định nếu FE muốn đơn giản; ghi rõ lựa chọn nào cũng được miễn nhất quán.
- **Rủi ro:** người dùng tưởng "nhập xong là có nhãn AI" → thất vọng khi bảng trống nhãn. Giảm nhẹ: toast + placeholder ở snippet cột đã nêu; dashboard/analysis nhắc chạy run khi tồn tại row chưa xử lý (UF-03 empty state).

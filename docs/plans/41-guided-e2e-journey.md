# Guided E2E journey — UX/UI plan

> **For agentic workers:** execute INLINE; no subagents. FE-only, no new dependencies, no endpoint change.

**Goal:** Người dùng đi hết luồng nhập → phân loại → hỏi AI & duyệt → chọn hành động → bàn giao mà không phải đoán bước tiếp theo hay đọc hướng dẫn.
**Spec:** Owner request 2026-11-03 (chạy hệ thống trên localhost:3000/8888, tối ưu UX/UI cho luồng end-to-end).

## Vấn đề quan sát trên hệ thống thật (2026-11-03)

1. Sidebar chia theo khung VoC (Lắng nghe / Hiểu / Hành động) với 7 mục ngang hàng; không nói thứ tự, không cho biết bước nào xong. Taxonomy (cấu hình nâng cao) nằm giữa luồng chính.
2. Không có chỉ dẫn "làm gì tiếp": hết import phải tự biết sang Vault bấm "Analyze pending items", rồi sang Data Graph tự nghĩ câu hỏi, rồi tự tìm Matrix.
3. Vault "All imports" + "Analyze pending items" lấy `imports[0]` làm phạm vi — có thể là file không còn mục chờ.
4. Trạng thái tải hiển thị như trạng thái rỗng ("Chọn một product", "No reviewed report yet") trong vài giây do DB ở xa.
5. Matrix không có hành động: phải quay sang Reports mới tạo được gợi ý.
6. Importer: ô nguồn "coming later", khối "How it works" và FirstRunGuide trùng ý nhau, chữ Anh/Việt lẫn lộn trên đường chính.

## Thiết kế

- **Lộ trình 5 bước** thay danh sách nav: `1 Nhập phản hồi → 2 Phân loại → 3 Hỏi AI & duyệt → 4 Chọn hành động → 5 Bàn giao`; mỗi bước hiện trạng thái thật (xong / đang làm / chờ) và số đếm. Báo cáo + Bộ chủ đề chuyển xuống nhóm "Tra cứu".
- **Dải "Bước tiếp theo"** đầu mọi màn của lộ trình: một câu nói việc cần làm + đúng một nút chính. Trạng thái suy ra thuần túy từ API (`lib/journey.ts`, có unit test), không lưu local.
- **Intent qua URL** để nút chính làm luôn việc: `/importer?new=1` mở bước chọn file, `/vault?import=<id>&analyze=1` mở biên nhận phân loại, `/data-graph?ask=1` focus ô hỏi.
- Mỗi điểm kết thúc của một màn có CTA sang bước kế (import xong → Phân loại; phân loại xong → Hỏi AI; kết luận duyệt → hành động; ma trận → bàn giao).
- Data Graph: câu hỏi gợi ý bấm-là-hỏi. Matrix: tạo gợi ý hành động ngay tại chỗ.

## Tasks

- [x] 1. `lib/journey.ts` + test: suy ra trạng thái 5 bước và hành động kế tiếp (16 test).
- [x] 2. `hooks/use-journey.ts` dùng chung cache TanStack; `components/journey/*` (rail sidebar, dải bước tiếp theo); i18n vi/en.
- [x] 3. Sidebar + breadcrumb dùng lộ trình; đổi nhãn nav theo động từ của bước.
- [x] 4. Importer gọn lại + intent `new`; chọn file là tải lên; kết quả import → CTA phân loại; mapping tự xử lý cột trùng đích (3 test).
- [x] 5. Vault: intent `analyze` + `reclassify`, sửa phạm vi "All imports", khoá nút khi đang chạy, CTA "Hỏi AI" sau khi phân loại xong.
- [x] 6. Data Graph: câu hỏi gợi ý + intent `ask`, thẻ điều tra lên trên; Matrix: loading đúng, tạo + quyết định hành động tại chỗ; Taxonomy: intent `generate`; onboarding vào thẳng bước chọn file.
- [x] 7. Kiểm chứng: vitest, tsc, eslint các file đụng tới; đi lại luồng trên trình duyệt (tài khoản seed + tài khoản mới).

## Phát hiện thêm khi chạy thật (đã xử lý trong plan này)

- Workspace mới chưa có bộ chủ đề → phân loại ra UNCATEGORIZED toàn bộ: lộ trình chèn bước con "Tạo bộ chủ đề" trước phân loại và "Phân loại lại" khi mọi mục đều UNCATEGORIZED.
- AI mapping đề xuất 2 cột cùng `feedback_text` → server 422: UI tự giữ một cột, cột còn lại "Bỏ qua" kèm giải thích.

## Validation

`npm exec -- vitest run` · `npm exec -- tsc --noEmit` · focused `npm exec -- eslint <files>` · browser walk-through localhost:3000.

# Sổ cái minh chứng của khóa luận

Tệp này giữ một dòng cho mỗi phát biểu có thể bị hiểu nhầm là kết quả thực nghiệm. Khi cập nhật Chương 4, tác giả phải mở đúng nguồn, kiểm tra phiên bản và ghi ngày. Không sao chép số từ tài liệu cũ nếu điều kiện chạy đã đổi.

| Mã | Phát biểu được phép dùng | Nguồn trực tiếp | Trạng thái 24/9/2026 | Giới hạn bắt buộc nêu |
|---|---|---|---|---|
| E01 | Khảo sát có 36 câu trả lời đồng ý; 25 chọn 101–500 feedback/tháng | CSV khảo sát trong `docs/thesis/` | Đã đếm lại bằng `csv.DictReader` | Mẫu thuận tiện; không có suy rộng dân số |
| E02 | 20 người “thỉnh thoảng”, 16 người “thường xuyên” phát hiện muộn vấn đề lặp | CSV khảo sát | Đã đếm lại | Là tự thuật, không phải đo thời gian thực tế |
| E03 | Frontend unit: 39/39 đạt | `frontend/node_modules/.bin/vitest.cmd run` | Chạy mới, exit 0 | Không đo trải nghiệm người dùng |
| E04 | Backend unit không integration: 76 đạt, 1 lỗi, 4 bỏ qua | `backend/.venv/Scripts/python.exe -m pytest -m 'not integration' -q` | Chạy mới; exit 1 | Lỗi Stanza bị chặn đọc `resources.json` ngoài workspace; không ghi “green” |
| E05 | Typecheck frontend chưa đạt | `tsc --noEmit` | Chạy mới; exit 1 | `.next/dev/types/validator.ts` sinh lỗi; chưa kết luận mã nguồn TS sai |
| E06 | Phân cụm 25 phản hồi: 25 noise với min cluster size 5/8/10/15 | `docs/evidence/cluster-sweep-results.json` | Nguồn có sẵn, chưa tái chạy | Bộ nhỏ; không suy ra thuật toán luôn thất bại |
| E07 | Foundation 22 phản hồi ~4m26s, tìm tương tự ~280ms | `docs/backend-foundation-report.md` | Minh chứng 25/8/2026 | Kiến trúc và điều kiện mạng cũ; không dùng cho phiên hiện tại |
| E08 | Spike S1–S6 ghi kết quả kỹ thuật | `docs/decisions.md`, `scripts/spikes/` | Minh chứng lịch sử tháng 8 | Spike toy/giới hạn; không thay thế E2E hiện tại |
| E09 | Demo 5 phản hồi qua Gate 1–3, tạo 7 action, sửa score 8,10→7,40 | `docs/handoffs/2026-09-15-claude-code-fe12-six-screens.md` | Handoff có ghi kịch bản, chưa tái chạy | Một kịch bản, không phải trung bình hay hiệu quả chung |
| E10 | UNDERSTAND đã được thử trên dữ liệu giả lập với evidence và tracing | `docs/handoffs/2026-09-02-codex-agent-live-synthetic-test.md` | Handoff ghi thành công và lỗi vòng đời | Run `running` sau approve; không nói graph đã hoàn thiện |
| E11 | Bộ metadata demo 650 dòng chỉ là dấu vết kế hoạch cũ | `docs/evidence/demo-dataset-shape.json` | Tệp demo CSV hiện có 19 dòng | Không dùng 650 làm mẫu đánh giá hiện tại |
| E12 | VPS deploy chưa hoàn tất | `infra/setup_vps.sh` | Script còn placeholder | Không ghi có production deployment |

## Các minh chứng cần bổ sung để khóa bản nộp

1. Chốt commit hoặc tag, lưu `git status` sạch và hash vào Chương 4.
2. Chạy backend unit trên môi trường có quyền đọc `D:/stanza_resources/resources.json`; ghi rõ `pii_mode` ở health và test pass/fail.
3. Tạo lại artifact `.next/dev/types`, chạy `tsc --noEmit`, lint, build và giữ log tóm tắt.
4. Chạy nhóm integration trên project Supabase thử nghiệm được phép; lưu tổng số đạt/bỏ qua, ngày và migration head.
5. Chạy một E2E xuyên sáu màn hình trên dữ liệu giả lập mới; lưu ảnh giao diện thật và ID run đã che định danh.
6. Nếu muốn báo chất lượng phân loại: chuẩn bị bộ nhãn tham chiếu có quy trình chấm và tính chỉ số từ dự đoán tương ứng.
7. Nếu muốn báo giảm thời gian xử lý: thiết kế đối chứng giữa quy trình thủ công và hệ thống, cùng phạm vi công việc và người thực hiện.
8. Có bản Turnitin thật, chữ ký GVHD và thông tin bìa trước khi xuất PDF nộp Khoa.

## Phân biệt dạng phát biểu

- **Đã triển khai:** kiểm tra trong `backend/app`, `frontend/app`, migrations và API checklist.
- **Đã chạy:** có lệnh, ngày và đầu ra cụ thể.
- **Đã thiết kế:** có trong `docs/plans/` hoặc `docs/design/`, chưa chắc có mã nguồn đang dùng.
- **Giả định/minh họa:** câu chuyện trong `docs/ai-agent-success-story.md` và ảnh thiết kế.
- **Chưa có chứng cứ:** mọi khẳng định về độ chính xác AI, tác động kinh doanh, bản production VPS hoặc thử nghiệm người dùng quy mô lớn chưa có phép đo phù hợp.

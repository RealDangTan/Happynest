# 43 — Sắp lại Chương 3 khóa luận (v6 → v7)

**Trạng thái (24/11/2026):** D1 chốt — giữ Hình 3.3. Phần A xong, ghi ra `chuong3-v8.docx` (v7 đang mở trong Word; v8 = v7 + sắp lại 3.2.2: nguyên tắc và ba điểm kiểm duyệt đứng trước, biểu đồ hoạt động + chú giải màu đứng sau). Dựng lại: `docs/thesis/v7-src/apply_v7.ps1 -Dst ...v8.docx`. Phần B chưa làm.

Nguồn: phản biện Chương 3 ngày 24/11/2026. Không ghi đè v6 (Word đang mở v6); mọi thay đổi ghi ra `...-chuong3-v7.docx`.

## Hiện trạng kỹ thuật của docx (đã kiểm tra)

- Chú thích hình/bảng dùng trường `SEQ` (tự đánh số lại khi cập nhật trường trong Word). Mục lục, danh mục hình/bảng cập nhật được bằng Word.
- Tham chiếu trong thân bài ("Hình 3.4", "Bảng 3.12", "Mục 3.1.3") là **chữ thường, không phải trường REF** → khi đổi số phải đổi tay theo bảng ánh xạ. Số lần xuất hiện: Chương 3 ≈ 76 (Hình 40, Bảng 29, Mục 7); ngoài Chương 3: Ch1 ×1, Ch2 ×1, Ch4 ×6 (Bảng 3.12, Bảng 3.14, Mục 3.1.2, 3.1.3, 3.6.4).
- Số của tiêu đề (3.4.2…) là chữ gõ tay, không tự đánh số.
- Có 4 ghi chú (comment) của tác giả trong file, giữ nguyên.

## Phần A — chỉ trong Chương 3 (làm ngay, rủi ro thấp)

| # | Việc | Ảnh hưởng đánh số |
|---|---|---|
| A1 | ~~Mục 3.4.1: bỏ Hình 3.3 (luồng sử dụng, trùng Hình 3.1–3.2), thay nội dung Bảng 3.4 bằng **bảng truy vết** bước nghiệp vụ → yêu cầu F → use case → hình/bảng đặc tả. Tên mục đổi thành "Truy vết từ quy trình nghiệp vụ đến use case" | ~~Hình 3.4…3.20 → 3.3…3.19~~ — **hủy do D1**: giữ Hình 3.3; thay vào đó Bảng 3.4 thêm cột "Yêu cầu", "Use case" và dòng F12, Hình 3.3 đổi màu AI cam → xám và ô cuối thành "Phương án đã chọn". Không đánh số lại |
| A2 | Một bảng chú giải màu duy nhất đặt đầu Mục 3.2; sửa đoạn chú giải ở đầu 3.4 (dòng "Các biểu đồ trong chương…") cho khớp: xanh nhạt = quyết định/điểm kiểm duyệt của người phụ trách, xám = gọi dịch vụ AI, trắng = chương trình | không |
| A3 | Sửa mâu thuẫn: dòng "Hành động" của bảng truy vết/3.4.1 không nói "gửi bản tin cho phòng ban" (trái 3.2.2 và 1.4.3); nêu rõ quy trình dừng ở chọn phương án | không |
| A4 | Mỗi nhóm 3.4.3–3.4.10 theo thứ tự: biểu đồ use case → đặc tả → (biểu đồ hoạt động nếu có), mỗi hình ở Chương 4 sẽ trỏ ngược về bảng đặc tả (làm ở phần B) | không |

Ánh xạ hình (CHỈ áp dụng nếu sau này bỏ Hình 3.3; hiện không dùng): 3.1→3.1, 3.2→3.2, **3.3 bỏ**, 3.4→3.3, 3.5→3.4, 3.6→3.5, 3.7→3.6, 3.8→3.7, 3.9→3.8, 3.10→3.9, 3.11→3.10, 3.12→3.11, 3.13→3.12, 3.14→3.13, 3.15→3.14, 3.16→3.15, 3.17→3.16, 3.18→3.17, 3.19→3.18, 3.20→3.19.

## Phần B — xuyên chương (gộp làm một lượt với sửa Chương 1 và Chương 4, để đánh số lại một lần)

| # | Việc |
|---|---|
| B1 | Chuyển 3.5.1 (Design Science Research) sang Chương 1, mục "Phương pháp nghiên cứu" mới |
| B2 | Chuyển Bảng 3.12 (thử nghiệm kỹ thuật, có số liệu 66,7% che tên) sang Chương 4 (4.6), sửa các chỗ trích dẫn ở 4.6.1 |
| B3 | Đưa Hình 4.12–4.13 (trình tự đăng nhập) về cạnh Bảng 3.5/Hình 3.6, hoặc ngược lại |
| B4 | Chuyển Hình 3.18 (hoạt động lớp gọi mô hình) sang Chương 4 gần mục thiết kế bước có gọi AI; Hình 4.11 về cùng 4.2 |
| B5 | Mỗi hình hoạt động/trình tự ở 4.2–4.4 ghi "chi tiết bên trong bước … của use case … (Bảng 3.x)" |

Không làm: gộp biểu đồ gói 3.16/3.17 với biểu đồ thành phần 3.15 (vai trò khác nhau: chạy lúc vận hành vs. tổ chức mã); chỉ cần nêu rõ vai trò trong lời dẫn.

## Cách thực hiện

1. Sao `v6.docx` → `v7.docx`.
2. Sửa nội dung bằng Word COM (instance riêng, theo `v6-src/apply_v6.ps1`) hoặc chỉnh XML; thêm bảng truy vết, xóa Hình 3.3.
3. Đổi số theo bảng ánh xạ (hai lượt qua token tạm để không đè nhau), kể cả 8 chỗ ngoài Chương 3.
4. Cập nhật trường: chú thích, mục lục, danh mục hình/bảng.
5. Kiểm tra: trích lại văn bản, mọi "Hình/Bảng/Mục x.y" phải khớp tiêu đề thật; không còn chữ "Hình 3.20".

## Cần tác giả quyết trước

- **D1 (đã chốt):** cô yêu cầu giữ Hình 3.3 → giữ, mở rộng Bảng 3.4, không đánh số lại hình.
- **Còn mở:** chữ trong Hình 3.3 in ra chỉ cỡ ~5 pt (ảnh 596×1928 px bị co theo chiều cao trang) — nên xuất lại từ `user-flow.drawio` ở độ phân giải cao hoặc tách thành hai hình (khi đó phải đánh số lại, gộp vào Phần B).

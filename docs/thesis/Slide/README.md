# HappyNest — ảnh slide bảo vệ

Bộ ảnh slide được tạo trực tiếp bằng **Create Image / image_gen tích hợp**, theo yêu cầu ngày 12/10/2026. Không tạo tệp PowerPoint cho lần giao này.

## Cấu trúc

- `slide-01.png` đến `slide-12.png`: phần trình bày chính, theo khung dự kiến 9 phút 40 giây.
- `slide-13.png` đến `slide-18.png`: sáu chủ đề phụ lục phục vụ hỏi đáp.
- `source-outline.md`: khung nội dung người dùng cung cấp, lưu nguyên văn.
- `prompts.json`: toàn bộ prompt tạo ảnh và nguồn ảnh gốc.
- `verification.json`: kích thước, SHA-256 và kết quả kiểm tra bộ ảnh.

Ảnh giữ nguyên đầu ra raster của Create Image, bố cục ngang xấp xỉ 16:9. Chữ và sơ đồ đã nằm trong ảnh.

## Thứ tự

| Ảnh | Nội dung |
|---|---|
| 01 | Giới thiệu đề tài |
| 02 | Bài toán và căn cứ khảo sát |
| 03 | Mục tiêu và đóng góp |
| 04 | LISTEN · UNDERSTAND · ACT và các điểm duyệt |
| 05 | Kiến trúc và chuỗi truy vết |
| 06 | LISTEN và quản trị taxonomy |
| 07 | UNDERSTAND và cơ chế AI Agent |
| 08 | ACT và phê duyệt phương án |
| 09 | Tình huống minh họa xuyên suốt |
| 10 | Kết quả và phạm vi kiểm chứng |
| 11 | Giới hạn và kế hoạch đánh giá tiếp |
| 12 | Kết luận và trao đổi |
| 13 | Định vị với hệ thống liên quan |
| 14 | Vì sao cần Agent và cách giới hạn |
| 15 | Taxonomy, cluster và confidence |
| 16 | Công thức ưu tiên |
| 17 | Dữ liệu, kiểm thử và an toàn |
| 18 | Nguồn thực hành ACT và cấu hình mô hình |

## Nội dung và nhận diện

Nguồn chính là khung slide được đính kèm trong yêu cầu; tên trường và thông tin bìa đối chiếu với `Khoa-luan-Le-Dang-Tan-11236199-VoC.docx`. Ba ảnh `mascot.png`, `moodboard.png`, `UIchart.png` là tham chiếu phong cách: nền tối ấm, chữ ngà, olive và vàng dịu, mascot chim pixel.

Số liệu khảo sát và kiểm thử được trình bày theo nguồn lịch sử trong khung. Không chạy kiểm thử ứng dụng mới trong nhiệm vụ tạo ảnh. Các khung giao diện / tình huống giả lập là minh họa bằng ảnh sinh, không phải ảnh chụp ứng dụng hoặc bằng chứng của một lượt chạy mới. Phần hỏi đáp được rút gọn theo sáu chủ đề trong khung.

Ảnh tham chiếu gốc và mã nguồn ứng dụng được giữ nguyên. Việc tạo ảnh được chia cho ba subagent theo yêu cầu trực tiếp của người dùng; agent chính kiểm tra và lưu bộ ảnh.

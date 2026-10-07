# Phần đầu và Mở đầu

## Thông tin bìa

- Cơ sở đào tạo: ĐẠI HỌC KINH TẾ QUỐC DÂN — TRƯỜNG CÔNG NGHỆ — KHOA CÔNG NGHỆ THÔNG TIN.
- Loại tài liệu: KHÓA LUẬN TỐT NGHIỆP.
- Tên đề tài: AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI.
- Sinh viên: Lê Đăng Tấn; mã sinh viên: 11236199; lớp: CNTT65A; ngành: Công nghệ thông tin.
- Giảng viên hướng dẫn: TS. Lê Thị Hoài Thu. Thời điểm ghi trên bìa: tháng 12 năm 2026. Ký hiệu học kỳ trên gáy chờ xác nhận theo hệ thống của trường.
- Bìa phụ dành vị trí chữ ký giảng viên hướng dẫn. Gáy chỉ có học kỳ, ngành, tên sinh viên và mã sinh viên.

## Lời cam đoan

Tôi cam đoan khóa luận này trình bày trung thực quá trình tìm hiểu, phân tích, thiết kế và xây dựng hệ thống AI Agent hỗ trợ xử lý phản hồi người dùng về sản phẩm AI. Những nội dung tham khảo từ công trình và tài liệu khác được dẫn nguồn theo quy định. Các số liệu khảo sát, kết quả kiểm thử và giới hạn của hệ thống được nêu đúng theo phạm vi có thể kiểm chứng. Tôi chịu trách nhiệm về nội dung và tính trung thực của khóa luận.

**Ký tên và ghi rõ họ tên sau khi kiểm tra bản nộp cuối cùng.**

## Lời cảm ơn

Tôi xin cảm ơn giảng viên hướng dẫn và các thầy cô Khoa Công nghệ thông tin, Trường Công nghệ, Đại học Kinh tế Quốc dân đã hướng dẫn tôi trong quá trình thực hiện khóa luận. Tôi cảm ơn những người đã tự nguyện tham gia khảo sát về việc xử lý phản hồi người dùng. Các ý kiến này giúp tôi hiểu rõ hơn những khó khăn trong công việc và xác định phạm vi chức năng của hệ thống. Tôi cũng cảm ơn gia đình và bạn bè đã hỗ trợ trong thời gian học tập và thực hiện đề tài.

## Danh mục từ viết tắt

| Viết tắt | Giải nghĩa |
|---|---|
| AI | Artificial Intelligence — trí tuệ nhân tạo |
| API | Application Programming Interface — giao diện lập trình ứng dụng |
| CSV | Comma-Separated Values — tệp dữ liệu phân tách bằng dấu phẩy |
| CSDL | Cơ sở dữ liệu |
| HITL | Human-in-the-Loop — cơ chế con người tham gia quyết định |
| JSONB | Kiểu dữ liệu JSON nhị phân trong PostgreSQL |
| LLM | Large Language Model — mô hình ngôn ngữ lớn |
| PII | Personally Identifiable Information — thông tin định danh cá nhân |
| RBAC | Role-Based Access Control — kiểm soát truy cập theo vai trò |
| VoC | Voice of Customer — tiếng nói khách hàng |

## MỞ ĐẦU

Sản phẩm số tích hợp trí tuệ nhân tạo nhận phản hồi qua nhiều kênh và ở nhiều thời điểm. Một phản hồi có thể nói về lỗi chức năng, chất lượng câu trả lời của mô hình, trải nghiệm giao diện hoặc một lo ngại về an toàn. Để biến các phản hồi này thành quyết định sản phẩm, người phụ trách cần đọc, phân loại, tìm các vấn đề lặp lại, xác định mức ảnh hưởng và trình bày bằng chứng cho nhóm liên quan. Khi số lượng phản hồi tăng, công việc thủ công làm chậm việc nhận ra các tín hiệu mới và khó duy trì cách đánh giá nhất quán.

Khảo sát phục vụ đề tài thu được 36 phiếu đồng ý tham gia, từ những người tự cho biết đã xử lý phản hồi cho sản phẩm số có tính năng AI trong sáu tháng gần đây. Trong số đó, 25 người cho biết nhóm xử lý khoảng 101–500 phản hồi mỗi tháng; 20 người cho biết thỉnh thoảng và 16 người cho biết thường xuyên gặp tình huống nhận ra một vấn đề lặp lại sau khi đã xuất hiện nhiều phản hồi tương tự. Đây là mẫu khảo sát thuận tiện, có giá trị để định hướng thiết kế; số lượng và cách tuyển chọn mẫu không cho phép suy rộng tỷ lệ trên ra toàn bộ thị trường. Bảng tổng hợp và cách tính được trình bày ở Chương 1.

Xuất phát từ bài toán đó, khóa luận **“AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI”** đặt mục tiêu xây dựng một ứng dụng web hỗ trợ người quản lý sản phẩm và nhân sự vận hành đi từ dữ liệu phản hồi đến nhận định và lựa chọn hành động. Hệ thống tổ chức công việc thành ba giai đoạn. LISTEN tiếp nhận tệp, nhận diện cấu trúc và chuẩn hóa dữ liệu; UNDERSTAND phân tích phản hồi, điều tra bằng công cụ và tạo nhận định gắn với bằng chứng; ACT gợi ý các phương án xử lý và hỗ trợ người dùng ưu tiên. Người dùng xác nhận những quyết định quan trọng trong từng giai đoạn.

Khóa luận được thực hiện theo phương pháp xây dựng hệ thống phần mềm. Trước hết, tôi khảo sát nhu cầu và phân tích yêu cầu chức năng, phi chức năng. Tiếp theo, tôi mô hình hóa quy trình nghiệp vụ, thiết kế dữ liệu, API, giao diện và các thành phần xử lý AI. Hệ thống được hiện thực bằng Next.js, FastAPI, PostgreSQL/pgvector cùng các dịch vụ phân tích ngôn ngữ; chất lượng được xem xét qua kiểm thử chức năng, kiểm thử tích hợp và một số kịch bản xuyên suốt. Những nhận định về hiệu quả chỉ được đưa ra trong giới hạn dữ liệu và phép đo đã ghi nhận.

Nội dung báo cáo gồm bốn chương. Chương 1 trình bày bối cảnh, khảo sát, mục tiêu và phạm vi. Chương 2 giới thiệu cơ sở lý thuyết và các công nghệ được dùng để xây dựng giải pháp. Chương 3 phân tích nghiệp vụ và trình bày thiết kế hệ thống. Chương 4 mô tả kết quả xây dựng, kiểm thử, đánh giá và các giới hạn còn tồn tại. Phần kết luận tóm lược kết quả theo mục tiêu đặt ra và nêu hướng phát triển.

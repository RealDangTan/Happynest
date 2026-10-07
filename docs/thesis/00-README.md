# Hồ sơ biên soạn khóa luận AI Feedback Agent

Thư mục này chứa bản thảo phân mảnh và bản Word hợp nhất của khóa luận **“AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI”**. Mỗi tệp Markdown là một đơn vị công việc độc lập cho người hoặc agent được giao viết, rà soát và cập nhật. Bản Word là hiện vật đọc liên tục; nội dung phải đồng bộ với các tệp Markdown trước khi nộp.

## Thứ tự lắp ghép

| Thứ tự | Tệp | Trách nhiệm | Phụ thuộc trực tiếp |
|---|---|---|---|
| 1 | `01-phan-dau.md` | Bìa, lời cam đoan, lời cảm ơn, danh mục thuật ngữ và Mở đầu | Thông tin sinh viên, giảng viên |
| 2 | `02-chuong-1-tong-quan.md` | Bài toán, khảo sát, mục tiêu, phạm vi, yêu cầu cấp cao | Khảo sát tổng hợp; hiện trạng mã nguồn |
| 3 | `03-chuong-2-co-so-ly-thuyet.md` | Nền tảng lý thuyết, công trình và công nghệ liên quan | Nguồn học thuật trong `07-tai-lieu-tham-khao.md` |
| 4 | `04-chuong-3-phan-tich-thiet-ke.md` | Nghiệp vụ, yêu cầu, sơ đồ, kiến trúc, dữ liệu và giao diện | `docs/plans/21-27-voc-os-index.md`, mã nguồn hiện tại |
| 5 | `05-chuong-4-ket-qua-danh-gia.md` | Kết quả xây dựng, kiểm thử, số đo, giới hạn | `08-so-cai-minh-chung.md`; kiểm thử mới |
| 6 | `06-ket-luan.md` | Kết luận, hướng phát triển | Kết quả đã kiểm chứng ở Chương 4 |
| 7 | `07-tai-lieu-tham-khao.md` | Danh mục IEEE | Nguồn được trích trong nội dung |
| 8 | `09-phu-luc.md` | Đặc tả chi tiết, hợp đồng API, hướng dẫn chạy | Mã nguồn đã khóa phiên bản |

`08-so-cai-minh-chung.md` là sổ kiểm chứng cho toàn bộ bản thảo; `10-phan-cong-agent.md` là các gói nhiệm vụ và điểm bàn giao. Các tệp `RULES.md`, `sample_file.docx` và `dean-example_thesis.pdf` là đầu vào được giữ nguyên.
`11-gay-va-checklist-nop.md` ghi nội dung gáy dự kiến và danh sách việc hành chính còn cần hoàn tất.

## Quy tắc biên soạn

1. Quy định Khoa CNTT trong `RULES.md` là nguồn cao nhất cho trình bày: Times New Roman 13, giãn dòng 1,3, lề 3,5/2,5/2,5/2,5 cm (trái/phải/trên/dưới), trích dẫn IEEE, bốn chương và tối thiểu 50 trang nội dung chính.
2. Mã nguồn, migration và kiểm thử ở phiên bản chốt là nguồn cao nhất cho phát biểu **đã xây dựng**. Tài liệu thiết kế chỉ chứng minh **đã dự kiến**. Handoff và báo cáo cũ chỉ chứng minh **đã ghi nhận tại thời điểm đó**.
3. Dữ liệu khảo sát chỉ xuất hiện dưới dạng đếm và tỷ lệ tổng hợp. Không đưa tên, email, timestamp cá nhân, câu trả lời tự do hoặc feedback thô vào bản thảo, hình, prompt hay phụ lục.
4. Mọi chỉ số trong Chương 4 phải có mẫu số, ngày đo, lệnh hoặc quy trình tái lập, và phạm vi suy luận. Không đổi tên phép đo cấu trúc thành độ chính xác mô hình.
5. `docs/ai-agent-success-story.md` là câu chuyện giả định; các số trong đó không được dùng làm kết quả triển khai.
6. Không mô tả Docker hoặc triển khai VPS như năng lực đã chạy. Repo dùng Supabase managed PostgreSQL và backend native; `infra/setup_vps.sh` còn là placeholder.
7. Mỗi tác giả chỉnh đúng tệp được giao; mọi thay đổi làm lệch bảng dữ kiện phải cập nhật `08-so-cai-minh-chung.md`. Trước khi hợp nhất phải đối chiếu lại mục lục, hình/bảng, trích dẫn và số trang.

## Trạng thái bản nộp

`Khoa-luan-Le-Dang-Tan-11236199.docx` được dựng từ các tệp Markdown bằng `build_docx.py`. Bìa đã điền tên Lê Đăng Tấn, mã 11236199, lớp CNTT65A, ngành Công nghệ thông tin, GVHD TS. Lê Thị Hoài Thu và tháng 12/2026. Nội dung từ Mở đầu đến Kết luận được ước lượng 51 trang với khổ A4 và lề/font theo quy định; số trang thật phải kiểm trong Microsoft Word sau khi cập nhật field.

Trước khi phát hành bản PDF nộp Khoa vẫn cần xác nhận ký hiệu học kỳ cho gáy (dự kiến `2026-2027.1`), bổ sung chữ ký sinh viên và giảng viên hướng dẫn, chèn kết quả Turnitin thật, cập nhật mục lục/danh mục/công thức bằng Ctrl+A → F9, rồi xem từng trang và xuất PDF. Runtime hiện không có LibreOffice và Word COM không khả dụng, nên bản DOCX chưa qua kiểm tra dàn trang trực quan bằng Word. Các kết quả test phần mềm chưa hoàn toàn xanh được ghi nguyên trạng ở Chương 4.

Lệnh dựng lại (dùng Python có `python-docx` và Pillow): `python docs/thesis/build_docx.py`. Không chỉnh tay DOCX rồi quên cập nhật Markdown; thay đổi nội dung cần bắt đầu từ tệp được phân công và xây dựng lại.

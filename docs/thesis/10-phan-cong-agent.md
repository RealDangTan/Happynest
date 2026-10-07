# Gói công việc cho các agent biên soạn khóa luận

Mỗi gói có đầu vào, quyền sửa, đầu ra và cổng nghiệm thu. Các gói có thể được giao cho những phiên làm việc khác nhau nhưng phải tuân thủ `AGENTS.md` và skill `agent-handoff`: nhận việc theo handoff, không sửa tệp thuộc agent khác cùng lúc, không đưa dữ liệu cá nhân thô vào docs. Bản Word chỉ được build sau khi nội dung Markdown và sổ minh chứng nhất quán.

## Gói A — Hình thức và phần đầu

- **Sở hữu:** `01-phan-dau.md`, thông tin bìa trong DOCX.
- **Đầu vào:** `RULES.md`, `sample_file.docx`, tên đề tài, thông tin sinh viên/GVHD đã được chủ sở hữu xác nhận.
- **Công việc:** kiểm tra bìa chính/phụ/gáy, lời cam đoan, lời cảm ơn, thuật ngữ và Mở đầu. Không ký thay sinh viên/GVHD, không tạo Turnitin giả.
- **Nghiệm thu:** mọi trường bìa khớp thông tin thật; thứ tự phần đầu và đánh số trang đúng mẫu; Mở đầu 1–2 trang.

## Gói B — Bài toán và khảo sát

- **Sở hữu:** `02-chuong-1-tong-quan.md` (gồm mục 1.7–1.9), số liệu khảo sát ở `09-phu-luc.md`.
- **Đầu vào:** CSV khảo sát trong thư mục thesis, chỉ xử lý tổng hợp; `AGENTS.md`, README.
- **Công việc:** đối chiếu từng số đếm và tỷ lệ, mô tả hạn chế mẫu, nối kết quả khảo sát với yêu cầu hệ thống. Không xuất cột tên, email, câu trả lời tự do.
- **Nghiệm thu:** bảng có n=36, tổng đúng, tỷ lệ làm tròn có chú thích; Chương 1 dài 5–10 trang và không suy rộng quần thể.

## Gói C — Cơ sở lý thuyết và trích dẫn

- **Sở hữu:** `03-chuong-2-co-so-ly-thuyet.md` (gồm mục 2.8–2.10), `07-tai-lieu-tham-khao.md`.
- **Đầu vào:** các bài báo và tài liệu gốc ở danh mục IEEE; mã nguồn để biết hệ thống thật sự dùng gì.
- **Công việc:** kiểm tra tác giả, năm, DOI/URL, mỗi phát biểu được dẫn đúng nguồn; phân biệt Sentence-BERT là lý thuyết với embedding provider thực tế; không gọi hệ thống là RAG nếu không có pipeline RAG tương ứng.
- **Nghiệm thu:** Chương 2 dài 10–15 trang; nguồn chỉ gồm tài liệu đã dẫn; thứ tự IEEE đúng lần xuất hiện; không có trích dẫn không truy được.

## Gói D — Nghiệp vụ, yêu cầu và use case

- **Sở hữu:** các mục 3.1–3.3 trong `04-chuong-3-phan-tich-thiet-ke.md`, Phụ lục A.
- **Đầu vào:** `docs/api-checklist.md`, `docs/design/2026-09-15-ui-flow/01-user-flow-ascii.md`, mã router hiện tại.
- **Công việc:** chốt F01–F10, N01–N06, tác nhân, quyền và ba Gate; đối chiếu đường ngoại lệ của use case với API.
- **Nghiệm thu:** mỗi ca quan trọng có tiền điều kiện, đường chính, lỗi và hậu điều kiện; không ghi các nhóm chức năng ACT thành vai trò đăng nhập.

## Gói E — Kiến trúc và dữ liệu

- **Sở hữu:** các mục 3.4–3.5, 3.8, 3.10–3.13, sơ đồ kiến trúc, ERD, Phụ lục B.
- **Đầu vào:** `backend/app/main.py`, models, migrations 0008–0015, `docs/decisions.md`.
- **Công việc:** rà ranh giới frontend/API/DB/LLM/tracing; dựng ERD theo bảng còn tồn tại; đối chiếu local raw-file storage và PostgreSQL; mô tả PII boundary.
- **Nghiệm thu:** mỗi tên bảng/quan hệ có trong migrations; không lẫn series 17–20; sơ đồ có nguồn và được dẫn trong thân bài.

## Gói F — AI pipeline và Agent

- **Sở hữu:** mục 3.6, sơ đồ graph, giải thích công thức 3.1.
- **Đầu vào:** classifier, embedder, clustering, `backend/understand_agent/`, ACT service, settings và các test tương ứng.
- **Công việc:** đối chiếu node/edge/công cụ thật, ngưỡng/cap, cơ chế evidence whitelist, ACT relevance và priority. Tách finding với hypothesis.
- **Nghiệm thu:** công thức có ký hiệu/miền giá trị; graph khớp code; không khẳng định có mô hình tự huấn luyện hoặc ACT graph nếu code không có.

## Gói G — Giao diện và kịch bản demo

- **Sở hữu:** mục 3.7, 3.9, các mục 4.2 và 4.5, ảnh được đưa vào DOCX.
- **Đầu vào:** frontend sáu màn hình, FE-12/FE-13, UI flow, dữ liệu demo giả lập.
- **Công việc:** chụp ảnh ứng dụng chạy thật sau khi có môi trường; giữ ảnh thiết kế ở Chương 3 với nhãn “thiết kế”; mô tả một hành trình có ID run và trạng thái được xác minh.
- **Nghiệm thu:** ảnh không lộ PII, được đánh số/chú thích/dẫn chiếu; không dùng handoff thay phép chạy mới.

## Gói H — Kiểm thử và đánh giá

- **Sở hữu:** các mục 4.1, 4.3, 4.4, 4.6–4.9; `08-so-cai-minh-chung.md`.
- **Đầu vào:** test suite, sổ lỗi, Supabase test project được phép, cấu hình Stanza và frontend build.
- **Công việc:** chạy lại lệnh trên commit khóa sổ; ghi cả test lỗi và skip; nếu muốn F1 hay time saving phải có nhãn chuẩn hoặc đối chứng hợp lệ.
- **Nghiệm thu:** mỗi chỉ số có ngày, môi trường, mẫu số và lệnh tái lập; không để số kết quả cũ như kết quả hiện tại.

## Gói I — Hợp nhất và kiểm tra bản nộp

- **Sở hữu:** `06-ket-luan.md`, DOCX cuối, mục lục/danh mục hình bảng, rà soát toàn văn.
- **Đầu vào:** gói A–H đã nghiệm thu, `RULES.md`, mẫu Word gốc, bản Turnitin thật nếu đã có.
- **Công việc:** chạy `build_docx.py` và `verify_docx.py`, kiểm tra thứ tự mục, số trang nội dung tối thiểu 50 trên Word thật, IEEE, mọi bảng/hình được nhắc tới, lề/font/giãn dòng, thông tin bìa, chữ ký và phụ lục. Kết luận chỉ nhắc kết quả có trong Chương 4.
- **Nghiệm thu:** DOCX được mở và cập nhật field trong Microsoft Word, xuất PDF, xem tất cả trang, có chữ ký GVHD và Turnitin thật trước khi in/nộp.

## Thứ tự nhận việc

Gói A–C có thể được biên tập độc lập về nội dung; D và E làm nền cho F; G và H cần bản ứng dụng chạy và phiên bản mã đã chốt; I là bước hợp nhất cuối. Nếu nhiều agent tham gia, dùng worktree riêng cho từng phiên và ghi handoff append-only. Người hợp nhất giải quyết mâu thuẫn số liệu bằng `08-so-cai-minh-chung.md`, không lựa chọn theo bản văn nghe thuyết phục hơn.

# PHỤ LỤC

## Phụ lục A. Hệ thống chức năng và ca sử dụng

### A.1. Ma trận tác nhân và chức năng

| Nhóm chức năng | PM | Operations | Bằng chứng hiện thực |
|---|---|---|---|
| Đăng nhập, xem product, xem phản hồi | Có | Có | Router auth, products, feedback |
| Nhập CSV, duyệt mapping, chạy phân tích | Theo guard API | Theo guard API | Router imports và analysis |
| Đặt câu hỏi Agent và duyệt insight | Theo guard API | Theo guard API | Router agent |
| Chỉnh sửa/xóa thực thể quản trị | Có khi route `pm` | Không khi route `pm` | Router feedback, products, insights |
| Xem báo cáo và hành động | Theo guard API | Theo guard API | Router admin, actions |

Ma trận A.1 mô tả nhóm chức năng; trước khi nộp cần đối chiếu lại từng guard trong `backend/app/api/routes/` và `docs/api-checklist.md` của commit khóa sổ. Cột “Theo guard API” tránh suy đoán một quyền thống nhất cho mọi endpoint trong cùng nhóm.

### A.2. Đặc tả rút gọn UC01 — Xác nhận ánh xạ CSV

- **Tác nhân:** người dùng đã đăng nhập và chọn product.
- **Tiền điều kiện:** import có hồ sơ cột; sau khi yêu cầu đề xuất, trạng thái là `mapping_review`.
- **Luồng chính:** mở proposal → xem từng cột nguồn → giữ hoặc sửa quyết định → xác nhận → hệ thống kiểm tra → bắt đầu nhập → theo dõi đến `imported` hoặc `failed`.
- **Đường ngoại lệ:** thiếu cột nội dung, hai cột cùng trường đích, cột mơ hồ chưa xử lý, import đã đổi trạng thái.
- **Hậu điều kiện:** schema tương ứng được lưu; phản hồi nhập từ tệp có văn bản đã che và được gắn product/import.

### A.3. Đặc tả rút gọn UC02 — Duyệt insight

- **Tác nhân:** người dùng có quyền trên endpoint quyết định run.
- **Tiền điều kiện:** run UNDERSTAND đã tạo bản nháp và đang chờ Gate 2.
- **Luồng chính:** mở Reports → đọc finding, hypothesis, evidence và giới hạn → duyệt hoặc sửa → backend tiếp tục graph → lưu trạng thái cuối.
- **Đường ngoại lệ:** người dùng chọn `investigate_more`, graph quay về planner; yêu cầu lặp sau khi đã hoàn thành được kiểm tra theo trạng thái run; văn bản sửa được che PII.
- **Hậu điều kiện:** quyết định được lưu, insight có trạng thái phù hợp để hiển thị hoặc chuyển sang ACT.

### A.4. Đặc tả rút gọn UC03 — Duyệt action

- **Tác nhân:** người dùng có quyền xem/sửa action.
- **Tiền điều kiện:** insight đã được duyệt; action hợp lệ đã được sinh.
- **Luồng chính:** xem ma trận → mở action → so ước lượng AI với đánh giá của mình → sửa hoặc chấp nhận → backend tính lại điểm → ghi lịch sử.
- **Đường ngoại lệ:** action bị từ chối; người dùng hủy bản sửa chưa lưu; action đã thay đổi ở phiên khác cần tải lại.
- **Hậu điều kiện:** trạng thái và giá trị có hiệu lực được lưu; giá trị do AI sinh còn để đối chiếu.

## Phụ lục B. Danh mục API theo nhóm

Danh mục dưới đây là bản rút gọn để người đọc định vị các hợp đồng. Trạng thái, guard và request/response chính xác cần xem `docs/api-checklist.md` của phiên bản khóa sổ.

| Nhóm | Endpoint tiêu biểu | Công dụng |
|---|---|---|
| Auth | `POST /api/auth/token`, `GET /api/auth/me` | Đăng nhập và nhận diện người dùng |
| Product | `GET/POST /api/products` | Chọn hoặc tạo phạm vi sản phẩm |
| Import | `POST /api/imports`, `GET /api/imports/{id}/preview` | Nhận tệp và xem hồ sơ cột |
| Mapping | `POST /api/imports/{id}/mapping/proposal`, `POST /api/imports/{id}/mapping/decision` | Đề xuất và Gate 1 |
| Feedback | `GET /api/feedbacks`, `GET /api/feedbacks/{id}/similar` | Xem và tìm phản hồi gần |
| Analysis | `POST /api/analysis/runs/preview`, `POST /api/analysis/runs` | Xem phạm vi và bắt đầu xử lý |
| UNDERSTAND | `POST /api/agent/runs`, `POST /api/agent/runs/{id}/decision` | Điều tra và Gate 2 |
| ACT | Router `/api/actions` | Tạo, xem và duyệt action |
| Báo cáo | `GET /api/reports/summary`, `GET /api/reports/kpis` | Tổng hợp và KPI |

## Phụ lục C. Số liệu khảo sát tổng hợp

Nguồn là tệp CSV khảo sát lưu trong thư mục thesis; số quan sát hợp lệ ở các câu hỏi được dùng là 36. Tất cả người trả lời đã đồng ý tham gia và trả lời có kinh nghiệm xử lý phản hồi sản phẩm AI trong sáu tháng trước khảo sát. Phụ lục này không chứa định danh cá nhân hoặc câu trả lời tự do. Một câu có các mức được lưu dưới dạng `4` hoặc `3 - Trung bình`; khi tổng hợp, số đầu được coi là điểm Likert tương ứng.

| Câu hỏi | Mức 2 | Mức 3 | Mức 4 | Mức 5 | Tổng |
|---|---:|---:|---:|---:|---:|
| Phản hồi phân tán nhiều nguồn — mức khó khăn | 0 | 12 | 23 | 1 | 36 |
| Đọc/gán loại thủ công — mức khó khăn | 0 | 15 | 21 | 0 | 36 |
| Nhận ra chủ đề mới — mức khó khăn | 0 | 11 | 23 | 2 | 36 |
| Xác định ưu tiên — mức khó khăn | 5 | 31 | 0 | 0 | 36 |
| Tự động phân loại — mức hữu ích | 1 | 27 | 8 | 0 | 36 |
| Xác định cảm xúc/mức nghiêm trọng — mức hữu ích | 33 | 3 | 0 | 0 | 36 |
| Gom phản hồi tương tự — mức hữu ích | 2 | 7 | 27 | 0 | 36 |
| Phát hiện chủ đề mới — mức hữu ích | 0 | 14 | 21 | 1 | 36 |
| Insight kèm số lượng và ví dụ — mức hữu ích | 2 | 19 | 15 | 0 | 36 |

Các tỷ lệ trong Chương 1 được tính bằng `số lựa chọn / 36 × 100`, sau đó làm tròn một chữ số thập phân. Số phiếu và phạm vi ngày được đọc từ file nguồn; không đưa file CSV gốc vào phụ lục bản nộp vì có tên và địa chỉ email.

## Phụ lục D. Ma trận yêu cầu và kiểm chứng

| Yêu cầu | Nhóm kiểm thử hiện có | Bước kiểm tra thủ công cần cho bản nộp |
|---|---|---|
| F03–F04, N01 | `test_imports_listen.py`, `test_profiler_unit.py`, `test_presidio_service.py` | Xem preview đã che PII và import sau Gate 1 |
| F05, N03–N05 | `test_analysis_budget_unit.py`, `test_phase28_integration.py` | Preview → xác nhận phạm vi → tiến trình → kết quả |
| F06 | `test_similarity_roundtrip.py`, `test_clustering_unit.py` | Xem phản hồi gần và trường hợp không có cụm |
| F07–F08, N02 | `test_analytics_tools.py`, `test_understand_agent.py` | Đối chiếu finding với evidence, thử bốn quyết định Gate 2 |
| F09 | `test_act_agent.py` | Override điểm ở Gate 3, xem lịch sử trước/sau |
| F10 | `test_reports_service.py`, `test_decision_kpis.py` | Kiểm tra kỳ báo cáo và mẫu số |

## Phụ lục E. Hướng dẫn chạy và giới hạn tái lập

Ứng dụng cần môi trường Python 3.12, `uv`, Node/pnpm, Supabase PostgreSQL đã tạo extension vector và tệp `backend/.env` được điền theo `.env.example`. Không đưa `.env` thật vào tài liệu. Thứ tự cơ bản là cài backend, chạy Alembic, seed tài khoản, mở FastAPI trong terminal riêng; sau đó cài frontend và chạy Next.js trong terminal khác. Các lệnh cụ thể, cờ kiểm thử integration và lưu ý Windows đã có trong `README.md` ở repo gốc; bản nộp nên giữ phiên bản này đi kèm source thay vì chép thông tin khóa truy cập vào phụ lục.

Khi chạy demo, dùng product và tệp phản hồi giả lập riêng. Upload CSV trước; xem preview, mới yêu cầu mapping AI; xác nhận Gate 1; xem receipt và chọn phạm vi phân tích; sau đó đặt một câu hỏi cho Agent để tới Gate 2. Sau khi duyệt insight, tạo action và sửa một điểm ở Gate 3. Để tái lập phép đo, ghi lại thời điểm, model, số phản hồi, ID run, số lần thử fallback và tình trạng mạng. Không lấy số từ cửa sổ browser hiện tại nếu nó hiển thị dữ liệu của một lần chạy khác.

## Phụ lục F. Kết quả Turnitin

Phần này dành cho trang đầu của báo cáo kiểm tra Turnitin do cơ sở đào tạo cung cấp. Tại thời điểm biên soạn, sinh viên chưa có kết quả; không tạo hoặc mô phỏng báo cáo kiểm tra. Trang này chỉ được thêm vào bản nộp cuối sau khi có tài liệu thật.

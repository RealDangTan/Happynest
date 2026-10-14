# Tài liệu triển khai HappyNest

Hợp đồng hiện hành: mọi tài khoản đăng nhập dùng chung workspace, dữ liệu và toàn bộ chức năng. Người dùng có thể nhập liệu, phân tích, duyệt, sửa và xoá; các thao tác vẫn tuân thủ trạng thái nghiệp vụ, xác nhận chi phí và xác nhận xoá.

## Thứ tự đọc cho coding agent

1. `AGENTS.md`: stack, phạm vi và quy tắc làm việc.
2. Tài liệu này: hành vi hiện hành và nguồn đối chiếu.
3. [API checklist](api-checklist.md): endpoint, xác thực, schema và vị trí trên frontend.
4. [Kiến trúc](architecture/README.md): luồng dữ liệu, state machine và mô hình dữ liệu.
5. [Active board](plans/00-index.md) và [bàn giao](handoffs/README.md): công việc cần tiếp tục.

Mã nguồn hiện tại và API checklist quyết định hợp đồng triển khai. Các bản kế hoạch, kết quả thử nghiệm và ảnh minh hoạ ghi nhận ngữ cảnh của chúng; không dùng chúng để bổ sung yêu cầu khác với hợp đồng hiện hành. Khi tài liệu lệch mã nguồn, kiểm tra hành vi thực tế và cập nhật tài liệu trước khi triển khai tiếp.

## Danh tính và phiên đăng nhập

- Đăng ký/đăng nhập bằng email và mật khẩu; mật khẩu lưu bằng Argon2.
- JWT trong cookie httpOnly SameSite=Lax, hoặc Bearer cho CLI/Swagger.
- `UserOut = {id, email}`; JWT có `sub`, `iat`, `exp`.
- Mọi tài khoản đã xác thực sử dụng cùng danh sách products và cùng thao tác.
- `product_id`, `import_id`, `run_id` và các bộ lọc chỉ xác định dữ liệu nghiệp vụ được chọn.
- `reviewer_id` ghi nhận người đưa ra quyết định để đối chiếu lịch sử.
- Token thiếu/sai/hết hạn trả 401. Row không tồn tại trả 404; xung đột trạng thái 409; dữ liệu request sai 422.

## Các ranh giới cần giữ

Chỉ nội dung đã sanitize được đưa vào prompt, API response và trace. Dữ liệu thô ở vùng lưu trữ nội bộ. Ba cổng HITL xác nhận mapping, insight và action; nhận định phải có evidence, hành động có thể được người dùng chỉnh điểm trước khi nhận. Các thao tác tốn phí có preview/receipt và giới hạn run; xoá dữ liệu cần xác nhận trên giao diện.

Bộ lọc sản phẩm và lô nhập phải được truyền đúng qua truy vấn, evidence và giao diện. Kết quả trên một sản phẩm không được dùng để suy luận về sản phẩm khác khi người dùng đã chọn phạm vi cụ thể.

## Bằng chứng và tài liệu luận văn

- [Báo cáo kế hoạch](plan_report.md) và [decision log](decisions.md): trạng thái triển khai và quyết định kỹ thuật.
- [Báo cáo Backend Foundation](backend-foundation-report.md), [S7](s7-jev-evaluation.md), [ACT](act-best-practices-evaluation.md): kết quả trong phạm vi từng lần kiểm thử.
- `docs/thesis/`: bản Word, khung bảo vệ và các hình phục vụ luận văn.
- `docs/feedback-mock/`: dữ liệu synthetic phục vụ kiểm thử.

Số liệu kiểm thử lịch sử phải giữ ngày và phạm vi; không suy rộng thành chất lượng mô hình hoặc chứng nhận production.

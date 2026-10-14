# Hợp đồng workspace dùng chung

- Trạng thái: hoàn tất ngày 2026-10-14.
- Mục tiêu: mọi tài khoản đăng nhập dùng chung workspace, dữ liệu và toàn bộ thao tác.
- Nguồn triển khai: [API checklist](../api-checklist.md), [hướng dẫn tài liệu](../README.md).

## Hành vi

- [x] Cookie/Bearer xác thực danh tính; response người dùng gồm `{id, email}`.
- [x] Products, feedback, imports, runs, insights và actions dùng chung cho các tài khoản.
- [x] Bộ lọc product/import giữ phạm vi dữ liệu nghiệp vụ.
- [x] Người dùng có thể tạo, xem, sửa, xoá và đưa ra quyết định HITL.
- [x] Reviewer attribution, PII boundary, preview/receipt và xác nhận xoá được giữ.
- [x] Schema database ở revision 0019; dữ liệu nghiệp vụ được giữ.
- [x] Backend và frontend dùng cùng hợp đồng; tài liệu API và kiến trúc đồng bộ.

## Kiểm chứng ngày 2026-10-14

Backend: 124 unit tests và 1 PostgreSQL lifecycle test với hai tài khoản. Frontend: 50 tests, typecheck và production build. Scoped lint đạt; full lint còn lỗi effect tại Importer và cảnh báo activity-provider. Xem [bàn giao](../handoffs/2026-10-14-codex-shared-workspace.md).

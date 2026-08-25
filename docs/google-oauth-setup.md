# Hướng dẫn tạo Google OAuth client (cho đăng nhập Google — pha P1.5)

> Làm **một lần**, ~10 phút, cần đăng nhập Google account của bạn. Agent không làm thay được vì bước này yêu cầu đăng nhập Google Cloud Console.
> Xong xuôi chỉ cần dán 2 giá trị `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` vào `.env` — phần code nối sẽ làm ở pha P1.5 (plan FE-08).

## Các bước

1. **Mở** <https://console.cloud.google.com/> và đăng nhập tài khoản Google.
2. **Tạo project**: dropdown chọn project (góc trên trái) → **New Project** → tên gợi ý `happynest-thesis` → **Create** → đảm bảo project mới được chọn.
3. **Cấu hình OAuth consent screen**: menu ☰ → **APIs & Services → OAuth consent screen**
   - User Type: **External** → **Create**
   - App name: `Happynest`; chọn email hỗ trợ + email liên hệ developer của bạn
   - Scopes: bỏ qua, không cần thêm (luồng này chỉ xin profile + email cơ bản)
   - **Test users**: bấm **+ Add Users**, thêm địa chỉ Gmail bạn sẽ dùng để thử đăng nhập
     ⚠️ Bắt buộc — app đang ở chế độ *Testing* thì CHỈ email trong danh sách này login được.
4. **Tạo credential**: **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorized JavaScript origins: `http://localhost:3000`
   - Authorized redirect URIs: `http://localhost:3000/api/auth/google/callback`
   - **Create**
5. **Lấy thông tin**: hộp thoại hiện ra copy **Client ID** và **Client Secret** → dán vào `.env` (file gốc ở repo root; nếu `backend/.env` tồn tại thì đồng bộ cả hai):
   ```dotenv
   GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
   ```
6. *(Tuỳ chọn)* Trước ngày bảo vệ nếu muốn người khác ngoài test users cũng login được: OAuth consent screen → **Publish App** để thoát chế độ Testing.

## Lưu ý quan trọng

- **Redirect URI phải khớp chính xác từng ký tự** với callback route khi triển khai (`http://localhost:3000/api/auth/google/callback`) — lệch một chữ là lỗi `redirect_uri_mismatch`.
- Chế độ **Testing** giới hạn đúng các test users đã thêm — đủ dùng cho demo luận văn; chỉ Publish khi cần mở rộng.
- **Secret không bao giờ commit lên git** — chỉ nằm trong `.env` (đã gitignore). Nếu lỡ lộ, vào Credentials → xoá client và tạo lại.

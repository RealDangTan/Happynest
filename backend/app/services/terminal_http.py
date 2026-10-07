"""HTTP-only terminal adapter. Never automatically replay a mutation."""
from __future__ import annotations

import httpx


class TerminalError(RuntimeError):
    def __init__(self, message: str, *, status: int = 0, uncertain: bool = False):
        super().__init__(message)
        self.status = status
        self.uncertain = uncertain


class TerminalClient:
    def __init__(self, base_url: str, *, transport=None):
        self.http = httpx.Client(
            base_url=base_url.rstrip("/"), transport=transport,
            timeout=httpx.Timeout(900, connect=10), trust_env=False,
        )

    def request(self, method: str, path: str, **kwargs):
        try:
            response = self.http.request(method, path, **kwargs)
        except httpx.RequestError:
            uncertain = method.upper() not in {"GET", "HEAD"}
            raise TerminalError(
                "Mất kết nối/hết thời gian chờ. "
                + ("Yêu cầu có thể đã được xử lý; kiểm tra ID/trạng thái trước khi thử lại."
                   if uncertain else "Có thể tiếp tục kiểm tra trạng thái bằng ID."),
                uncertain=uncertain,
            ) from None
        if response.is_error:
            # Validation errors can contain the raw input; don't print the body.
            messages = {
                401: "Phiên đăng nhập không hợp lệ; đăng nhập lại.",
                403: "Tài khoản không có quyền thực hiện.",
                404: "Không tìm thấy ID/API. Kiểm tra BE đang chạy phiên bản mới.",
                409: "Trạng thái/số lượng đã thay đổi. Đọc lại trạng thái hoặc preview.",
                422: "Dữ liệu nhập không hợp lệ. Kiểm tra field, kiểu dữ liệu và giới hạn.",
                503: "Checkpoint/service chưa sẵn sàng. Giữ ID và kiểm tra lại sau.",
            }
            raise TerminalError(messages.get(response.status_code, "BE trả lỗi; kiểm tra log metadata."),
                                status=response.status_code,
                                uncertain=method.upper() != "GET" and response.status_code >= 500)
        return response.json() if response.content else {}

    def login(self, email: str, password: str):
        token = self.request("POST", "/api/auth/token", data={"username": email, "password": password})
        self.http.headers["Authorization"] = f"Bearer {token['access_token']}"
        return self.request("GET", "/api/auth/me")

    def close(self):
        self.http.headers.pop("Authorization", None)
        self.http.cookies.clear()
        self.http.close()

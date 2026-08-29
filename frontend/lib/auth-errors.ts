import { ApiError } from "@/lib/api";

export type AuthAlert = {
  variant: "destructive" | "warning";
  title: string;
  description: string;
};

/**
 * Map mọi lỗi của flow login/register thành alert thân thiện người dùng.
 * Nguyên tắc: lỗi người dùng (sai thông tin) → destructive; lỗi có thể tự khắc
 * phục (email trùng, validate, rate limit, timeout) → warning kèm hướng dẫn;
 * không bao giờ lộ message kỹ thuật raw.
 */
export function mapAuthError(error: unknown): AuthAlert {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return {
        variant: "destructive",
        title: "Sai email hoặc mật khẩu",
        description: "Kiểm tra lại thông tin đăng nhập rồi thử lại.",
      };
    }
    if (error.status === 409) {
      return {
        variant: "warning",
        title: "Email đã được đăng ký",
        description: "Email này đã có tài khoản. Bạn có thể đăng nhập luôn bên dưới.",
      };
    }
    if (error.status === 422) {
      return {
        variant: "warning",
        title: "Thông tin chưa hợp lệ",
        description: error.message || "Kiểm tra lại email và mật khẩu (tối thiểu 8 ký tự).",
      };
    }
    if (error.status === 429) {
      return {
        variant: "warning",
        title: "Thử quá nhiều lần",
        description: "Bạn đã thử nhiều lần liên tiếp. Đợi một lát rồi thử lại nhé.",
      };
    }
    if (error.status >= 500) {
      return {
        variant: "destructive",
        title: "Máy chủ gặp sự cố",
        description: "Lỗi từ phía máy chủ, không phải do bạn. Thử lại sau ít phút.",
      };
    }
    return {
      variant: "warning",
      title: "Không thực hiện được",
      description: error.message || "Đã có lỗi xảy ra. Thử lại nhé.",
    };
  }

  if (
    error instanceof DOMException &&
    (error.name === "AbortError" || error.name === "TimeoutError")
  ) {
    return {
      variant: "warning",
      title: "Hết thời gian chờ",
      description: "Kết nối chậm hoặc máy chủ không phản hồi. Kiểm tra mạng rồi thử lại.",
    };
  }

  return {
    variant: "destructive",
    title: "Không kết nối được máy chủ",
    description: "Kiểm tra kết nối mạng rồi thử lại.",
  };
}

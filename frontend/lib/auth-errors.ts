import type { AppLang } from "@/lib/i18n";
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
export function mapAuthError(error: unknown, lang: AppLang): AuthAlert {
  const vi = lang === "vi";
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return {
        variant: "destructive",
        title: vi ? "Sai email hoặc mật khẩu" : "Wrong email or password",
        description: vi
          ? "Kiểm tra lại thông tin đăng nhập rồi thử lại."
          : "Check your login details and try again.",
      };
    }
    if (error.status === 409) {
      return {
        variant: "warning",
        title: vi ? "Email đã được đăng ký" : "Email already registered",
        description: vi
          ? "Email này đã có tài khoản. Bạn có thể đăng nhập luôn bên dưới."
          : "This email already has an account. You can sign in right below.",
      };
    }
    if (error.status === 422) {
      return {
        variant: "warning",
        title: vi ? "Thông tin chưa hợp lệ" : "Invalid details",
        description:
          error.message ||
          (vi
            ? "Kiểm tra lại email và mật khẩu (tối thiểu 8 ký tự)."
            : "Check your email and password (at least 8 characters)."),
      };
    }
    if (error.status === 429) {
      return {
        variant: "warning",
        title: vi ? "Thử quá nhiều lần" : "Too many attempts",
        description: vi
          ? "Bạn đã thử nhiều lần liên tiếp. Đợi một lát rồi thử lại nhé."
          : "You've tried several times in a row. Wait a moment and try again.",
      };
    }
    if (error.status >= 500) {
      return {
        variant: "destructive",
        title: vi ? "Máy chủ gặp sự cố" : "Server error",
        description: vi
          ? "Lỗi từ phía máy chủ, không phải do bạn. Thử lại sau ít phút."
          : "This one is on the server, not you. Try again in a few minutes.",
      };
    }
    return {
      variant: "warning",
      title: vi ? "Không thực hiện được" : "Couldn't complete the request",
      description:
        error.message ||
        (vi ? "Đã có lỗi xảy ra. Thử lại nhé." : "Something went wrong. Try again."),
    };
  }

  if (
    error instanceof DOMException &&
    (error.name === "AbortError" || error.name === "TimeoutError")
  ) {
    return {
      variant: "warning",
      title: vi ? "Hết thời gian chờ" : "Request timed out",
      description: vi
        ? "Kết nối chậm hoặc máy chủ không phản hồi. Kiểm tra mạng rồi thử lại."
        : "The connection is slow or the server didn't respond. Check your network and try again.",
    };
  }

  return {
    variant: "destructive",
    title: vi ? "Không kết nối được máy chủ" : "Can't reach the server",
    description: vi
      ? "Kiểm tra kết nối mạng rồi thử lại."
      : "Check your network connection and try again.",
  };
}

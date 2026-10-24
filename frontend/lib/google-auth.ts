import { useCallback, useSyncExternalStore } from "react";
import type { AppLang } from "@/lib/i18n";
import type { AuthAlert } from "@/lib/auth-errors";

/** Route bắt đầu Google OAuth ở backend (đi qua proxy same-origin của Next). */
export const GOOGLE_LOGIN_URL = "/api/auth/google/login";

/**
 * Map mã lỗi backend trả về qua `?google_error=<mã>` khi callback Google
 * thất bại (xem `google_callback` trong `backend/app/api/routes/auth.py`).
 * Nguyên tắc giống mapAuthError: không lộ message kỹ thuật raw.
 */
export function googleErrorAlert(code: string | null, lang: AppLang): AuthAlert | null {
  const vi = lang === "vi";
  if (!code) return null;
  switch (code) {
    case "denied":
      return {
        variant: "warning",
        title: vi ? "Đã huỷ đăng nhập Google" : "Google sign-in cancelled",
        description: vi
          ? "Bạn đã từ chối trên trang Google. Bấm lại nút Google khi sẵn sàng."
          : "You declined on Google's page. Click the Google button again when ready.",
      };
    case "state":
      return {
        variant: "warning",
        title: vi ? "Phiên Google đã hết hạn" : "Google session expired",
        description: vi
          ? "Phiên chờ đăng nhập quá lâu hoặc không hợp lệ. Bấm lại nút Google."
          : "The pending sign-in session was too old or invalid. Click the Google button again.",
      };
    case "exchange":
      return {
        variant: "destructive",
        title: vi ? "Đăng nhập Google thất bại" : "Google sign-in failed",
        description: vi
          ? "Không xác thực được phản hồi từ Google. Thử lại, hoặc dùng email/mật khẩu."
          : "Couldn't verify Google's response. Try again, or use email and password.",
      };
    case "email_conflict":
      return {
        variant: "destructive",
        title: vi
          ? "Email đã liên kết tài khoản Google khác"
          : "Email is linked to a different Google account",
        description: vi
          ? "Email này đã nối với một tài khoản Google khác. Đăng nhập bằng Google hoặc email."
          : "This email is already linked to another Google account. Sign in with Google or email.",
      };
    default:
      return {
        variant: "warning",
        title: vi ? "Đăng nhập Google chưa hoàn tất" : "Google sign-in didn't finish",
        description: vi
          ? "Đã có lỗi không xác định. Thử lại hoặc đăng nhập bằng email."
          : "An unknown error occurred. Try again or sign in with email.",
      };
  }
}

/**
 * Đọc `?google_error=` sau khi Google redirect về. External state (location)
 * đọc qua useSyncExternalStore: server/hydration trả null (trang vẫn prerender
 * tĩnh được), giá trị xuất hiện sau khi mount — không dùng useSearchParams để
 * khỏi cần Suspense.
 */
export function useGoogleErrorParam(): string | null {
  const subscribe = useCallback((onChange: () => void) => {
    window.addEventListener("popstate", onChange);
    return () => window.removeEventListener("popstate", onChange);
  }, []);
  const getSnapshot = useCallback(() => {
    return new URLSearchParams(window.location.search).get("google_error");
  }, []);
  return useSyncExternalStore(subscribe, getSnapshot, () => null);
}

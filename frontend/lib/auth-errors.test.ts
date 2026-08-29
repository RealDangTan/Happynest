import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { mapAuthError } from "./auth-errors";

describe("mapAuthError", () => {
  it("401 → destructive, hướng dẫn thử lại", () => {
    const alert = mapAuthError(new ApiError(401, "Unauthorized"));
    expect(alert.variant).toBe("destructive");
    expect(alert.title).toMatch(/sai/i);
    expect(alert.description).not.toBe("Unauthorized");
  });

  it("409 → warning, gợi ý đăng nhập", () => {
    const alert = mapAuthError(new ApiError(409, "Conflict"));
    expect(alert.variant).toBe("warning");
    expect(alert.description).toMatch(/đăng nhập/i);
  });

  it("422 → warning, giữ detail từ server", () => {
    const alert = mapAuthError(new ApiError(422, "k < 1; k > 50"));
    expect(alert.variant).toBe("warning");
    expect(alert.description).toContain("k < 1");
  });

  it("429 → warning, khuyên đợi", () => {
    const alert = mapAuthError(new ApiError(429, "Too Many Requests"));
    expect(alert.variant).toBe("warning");
    expect(alert.title).toMatch(/nhiều lần/i);
  });

  it("5xx → destructive, đổ lỗi server không đổ lỗi người dùng", () => {
    const alert = mapAuthError(new ApiError(502, "Bad Gateway"));
    expect(alert.variant).toBe("destructive");
    expect(alert.description).toMatch(/máy chủ|thử lại/i);
  });

  it("fetch fail (TypeError) → destructive lỗi mạng", () => {
    const alert = mapAuthError(new TypeError("Failed to fetch"));
    expect(alert.variant).toBe("destructive");
    expect(alert.description).toMatch(/mạng/i);
  });

  it("AbortError timeout → warning hết thời gian chờ", () => {
    const abort = new DOMException("The operation was aborted.", "AbortError");
    const alert = mapAuthError(abort);
    expect(alert.variant).toBe("warning");
    expect(alert.title).toMatch(/thời gian/i);
  });

  it("lỗi lạ → destructive, không lộ message raw", () => {
    const alert = mapAuthError(new Error("ECONNRESET something odd"));
    expect(alert.variant).toBe("destructive");
    expect(alert.description).not.toContain("ECONNRESET");
  });
});

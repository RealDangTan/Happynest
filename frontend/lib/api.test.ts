import { describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./api";

describe("apiFetch", () => {
  it("trả JSON khi 2xx", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ok: true })));
    await expect(apiFetch("/x")).resolves.toEqual({ ok: true });
  });

  it("401 detail chuỗi → message = detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ detail: "Unauthorized" }, { status: 401 })),
    );
    const err = await apiFetch("/x").catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(401);
    expect((err as ApiError).message).toBe("Unauthorized");
  });

  it("401 → gọi POST /api/auth/logout (tự động kick về /login)", async () => {
    vi.resetModules();
    const { apiFetch: freshApiFetch, ApiError: FreshApiError } = await import(
      "./api"
    );
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/logout")
        return new Response(null, { status: 204 });
      return Response.json({ detail: "Unauthorized" }, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const err = await freshApiFetch("/api/imports").catch(
      (e: ApiError) => e,
    );
    expect(err).toBeInstanceOf(FreshApiError);
    expect((err as ApiError).status).toBe(401);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  });

  it("422 detail mảng FastAPI → join msg", async () => {
    const detail = [{ msg: "k < 1" }, { msg: "k > 50" }];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ detail }, { status: 422 })),
    );
    const err = await apiFetch("/x").catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toBe("k < 1; k > 50");
  });
});

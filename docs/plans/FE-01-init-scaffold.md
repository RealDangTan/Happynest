# FE-01 — Init scaffold + hạ tầng FE cơ bản

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng checkbox.
>
> **Goal:** `frontend/` thành app Next.js boot được, proxy `/api/*` về FastAPI, có provider query + wrapper fetch chuẩn hoá lỗi + test Vitest xanh.
>
> **Architecture:** Single Next.js App Router tại `frontend/` (không monorepo); mọi call API đi qua same-origin proxy rewrites để cookie httpOnly hoạt động.
>
> **Tech Stack:** Next.js (App Router, TS, Tailwind v4) · shadcn preset `b4IdeDqtkJ` radix · @tanstack/react-query · vitest.
>
> **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §4 · **Contract:** không gọi endpoint nào ngoài `/api/health` ở plan này.

## Global Constraints

- Không Docker; lệnh shadcn luôn `pnpm dlx shadcn@latest …`; commit nhỏ conventional + `Assisted-by: claude-code`.
- Chỉ đụng `frontend/` + file `FE-*`. Trước khi ghi file chung: re-read (roadmap §2).
- Windows: `pnpm dev` chạy RIÊNG một terminal; verify bằng curl từ terminal khác.

---

### Task 1: Preconditions

**Files:** Modify: none (chỉ kiểm tra + dọn placeholder)

- [ ] **Step 1: Check Node** — Run: `node --version`. Kỳ vọng `≥20.18.1`. Nếu thấp hơn → STOP, báo owner nâng cấp (blocker ghi `decisions.md`), không tự cài thay hệ thống.
- [ ] **Step 2: Dọn placeholder** — `git rm frontend/README.md` (nội dung placeholder đã lưu trong git history; README mới viết ở Task 6).
- [ ] **Step 3: Ghi nhận layout sau init** — chạy init ở Task 2 xong PHẢI `ls -R src` (hoặc tương đương) và cập nhật mục "Tiến độ log" của [`FE-00-index.md`](FE-00-index.md) nếu cấu trúc khác dự kiến `src/app`.

### Task 2: Init shadcn vào frontend/

**Files:** Create: toàn bộ scaffold trong `frontend/`

- [ ] **Step 1: Init** — từ repo root:
  ```bash
  cd frontend
  pnpm dlx shadcn@latest init --preset b4IdeDqtkJ --base radix --template next --pointer
  ```
- [ ] **Step 2: Fallback nếu CLI từ chối dir có file** — init với tên tạm rồi dồn lên:
  ```bash
  cd frontend
  pnpm dlx shadcn@latest init --name happynest-web --preset b4IdeDqtkJ --base radix --template next --pointer
  # rồi move TOÀN BỘ nội dung frontend/happynest-web/* lên frontend/ (kể cả dotfiles .gitignore),
  # xoá frontend/happynest-web rỗng
  ```
- [ ] **Step 3: Verify boot** — terminal riêng: `pnpm dev`; terminal khác: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` kỳ vọng `200`. Tắt dev.
- [ ] **Step 4: Commit**
  ```bash
  git add frontend
  git commit -m "feat(frontend): scaffold next app via shadcn preset b4IdeDqtkJ"
  ```

### Task 3: Proxy rewrites

**Files:** Modify: `frontend/next.config.ts`

- [ ] **Step 1: Sửa config**
  ```ts
  import type { NextConfig } from "next";

  const nextConfig: NextConfig = {
    async rewrites() {
      return [
        { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
      ];
    },
  };

  export default nextConfig;
  ```
- [ ] **Step 2: Verify xuyên hệ thống** — bật backend theo AGENTS (`uv run uvicorn app.main:app` — terminal riêng); `pnpm dev`; rồi:
  `curl -s http://localhost:3000/api/health` kỳ vọng JSON `{status, db, …}` (giống gọi thẳng :8000). Set-Cookie xuyên proxy kiểm lại ở FE-02 (login thật).
- [ ] **Step 3: Commit** — `git add frontend/next.config.ts && git commit -m "feat(frontend): proxy /api to fastapi for same-origin cookies"`

### Task 4: TanStack Query provider

**Files:** Create: `frontend/src/components/providers.tsx` · Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Cài** — `pnpm add @tanstack/react-query`
- [ ] **Step 2: Provider**
  ```tsx
  "use client";
  import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
  import { useState } from "react";

  export function Providers({ children }: { children: React.ReactNode }) {
    const [client] = useState(
      () =>
        new QueryClient({
          defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
        }),
    );
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  ```
- [ ] **Step 3: Wire root layout** — bọc `{children}` bằng `<Providers>` bên trong `<body>` của `src/app/layout.tsx`.
- [ ] **Step 4: Verify** — `pnpm build` xanh. Commit: `feat(frontend): tanstack query provider`

### Task 5: lib/api.ts + Vitest (TDD)

**Files:** Create: `frontend/src/lib/api.ts`, `frontend/src/lib/api.test.ts`, `frontend/vitest.config.ts` · Modify: `frontend/package.json` (scripts)

- [ ] **Step 1: Viết test TRƯỚC** — `pnpm add -D vitest`; `package.json` thêm `"test": "vitest run"`; tạo `vitest.config.ts`:
  ```ts
  import { defineConfig } from "vitest/config";
  import { fileURLToPath } from "node:url";

  export default defineConfig({
    test: { environment: "node" },
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  });
  ```
  Tạo `src/lib/api.test.ts` — 3 case:
  ```ts
  import { describe, expect, it, vi } from "vitest";
  import { ApiError, apiFetch } from "./api";

  describe("apiFetch", () => {
    it("trả JSON khi 2xx", async () => {
      vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ok: true })));
      await expect(apiFetch("/x")).resolves.toEqual({ ok: true });
    });

    it("401 detail chuỗi → message = detail", async () => {
      vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail: "Unauthorized" }, { status: 401 })));
      const err = await apiFetch("/x").catch((e: ApiError) => e);
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(401);
      expect((err as ApiError).message).toBe("Unauthorized");
    });

    it("422 detail mảng FastAPI → join msg", async () => {
      const detail = [{ msg: "k < 1" }, { msg: "k > 50" }];
      vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 422 })));
      const err = await apiFetch("/x").catch((e: ApiError) => e);
      expect((err as ApiError).message).toBe("k < 1; k > 50");
    });
  });
  ```
- [ ] **Step 2: Chạy thấy FAIL** — Run: `pnpm test`. Kỳ vọng: FAIL toàn bộ với lỗi module `./api` không tồn tại.
- [ ] **Step 3: Hiện thực tối thiểu** — tạo `src/lib/api.ts`, định nghĩa `ApiError` (dùng chung mọi plan sau, kể cả login form-encoded):
  ```ts
  export class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public detail?: unknown,
    ) {
      super(message);
      this.name = "ApiError";
    }

    static async from(res: Response): Promise<ApiError> {
      let message = res.statusText;
      let detail: unknown;
      try {
        const body = await res.json();
        detail = body?.detail ?? body;
        if (typeof detail === "string") message = detail;
        else if (Array.isArray(detail))
          message = detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
      } catch {
        /* body không phải JSON — giữ statusText */
      }
      return new ApiError(res.status, message, detail);
    }
  }

  export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(path, { credentials: "include", ...init });
    if (!res.ok) throw await ApiError.from(res);
    return (await res.json()) as T;
  }
  ```
- [ ] **Step 4: Chạy thấy PASS** — Run: `pnpm test`. Kỳ vọng: 3/3 PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/lib frontend/vitest.config.ts frontend/package.json && git commit -m "feat(frontend): api wrapper with normalized errors + vitest"`

### Task 6: README mới cho frontend/

- [ ] **Step 1: Viết** `frontend/README.md`: cách chạy (`pnpm install`, `pnpm dev`, yêu cầu backend :8000), kiến trúc proxy 2 câu, link về spec + contracts.
- [ ] **Step 2: Commit** — `git add frontend/README.md && git commit -m "docs(frontend): readme run + proxy notes"`

## Acceptance criteria

- [ ] `node --version` ≥ 20.18.1 (nếu không: blocker đã ghi decisions.md và owner biết)
- [ ] `pnpm dev` boot :3000; `curl localhost:3000/api/health` trả JSON thật từ FastAPI
- [ ] `pnpm build` xanh; `pnpm test` 3/3 PASS
- [ ] Mỗi task ≥ 1 commit; không đụng file ngoài lãnh thổ
- [ ] Evidence luận văn: screenshot trang mặc định + JSON health qua proxy

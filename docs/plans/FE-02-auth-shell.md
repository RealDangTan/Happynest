# FE-02 — Auth + App shell

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng checkbox.
>
> **Goal:** Đăng nhập thật qua proxy (cookie httpOnly set trên origin :3000), middleware chặn route chưa login, shell Sidebar với user box, các route P3/P4 có trang placeholder.
>
> **Architecture:** JWT vẫn do FastAPI cấp/xác minh; FE chỉ đọc *presence* của cookie trong middleware (edge runtime không xác minh chữ ký). Data user từ `GET /api/auth/me`.
>
> **Tech Stack:** Next.js middleware · TanStack Query · shadcn: sidebar, card, field, input, button, alert, spinner, dropdown-menu, avatar, badge, separator, empty.
>
> **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §4 · **Contract:** endpoint auth đã ship (`POST /api/auth/token`, `GET /api/auth/me`) — xem [`../api-notes.md`](../api-notes.md).

## Global Constraints

- Không tạo endpoint backend mới ở plan này (logout là limitation v1 — contracts §Non-goals).
- Form login gửi `application/x-www-form-urlencoded` với field `username`/`password` (OAuth2 password flow — KHÔNG phải JSON).
- Lỗi đăng nhập luôn hiển thị chung "Email hoặc mật khẩu sai" khi 401 (API cố ý không phân biệt — chống dò email).

---

### Task 1: Middleware guard

**Files:** Create: `frontend/src/middleware.ts`

- [ ] **Step 1: Code**
  ```ts
  import { NextResponse, type NextRequest } from "next/server";

  const PUBLIC_PATHS = ["/login"];

  export function middleware(req: NextRequest) {
    const hasSession = req.cookies.has("access_token");
    const { pathname } = req.nextUrl;

    if (!hasSession && !PUBLIC_PATHS.includes(pathname)) {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      return NextResponse.redirect(url);
    }
    if (hasSession && pathname === "/login") {
      const url = req.nextUrl.clone();
      url.pathname = "/feedbacks";
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
  };
  ```
- [ ] **Step 2: Verify bằng curl** (`pnpm dev` đang chạy):
  - `curl -s -o /dev/null -w "%{http_code} %{redirect_url}" http://localhost:3000/feedbacks` → `307 …/login`
  - `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/login` → `200`
  - `curl -s http://localhost:3000/api/health` → JSON (matcher không chặn `/api`)
- [ ] **Step 3: Commit** — `feat(frontend): session middleware guard`

### Task 2: Hook danh tính

**Files:** Create: `frontend/src/hooks/use-me.ts`

- [ ] **Step 1: Code**
  ```ts
  "use client";
  import { useQuery } from "@tanstack/react-query";
  import { apiFetch } from "@/lib/api";

  export type User = { id: string; email: string; role: "pm" | "operations" };

  export function useMe() {
    return useQuery({
      queryKey: ["me"],
      queryFn: () => apiFetch<User>("/api/auth/me"),
      staleTime: 5 * 60 * 1000,
      retry: false,
    });
  }
  ```
- [ ] **Step 2: Verify** — `pnpm build` xanh (hook dùng ở Task 4; chưa gọi đâu thì build đủ). Commit: `feat(frontend): use-me hook`

### Task 3: Trang đăng nhập

**Files:** Create: `frontend/src/app/login/page.tsx` · Add components

- [ ] **Step 1: Add components** — `pnpm dlx shadcn@latest add card field input button alert spinner`; đọc lại file vừa add để kiểm composition đúng rules (FieldGroup/Field, Alert có Title).
- [ ] **Step 2: Page code**
  ```tsx
  "use client";
  import { useState } from "react";
  import { useRouter } from "next/navigation";
  import { useMutation } from "@tanstack/react-query";
  import {
    Card, CardContent, CardDescription, CardHeader, CardTitle,
  } from "@/components/ui/card";
  import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
  import { Input } from "@/components/ui/input";
  import { Button } from "@/components/ui/button";
  import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
  import { Spinner } from "@/components/ui/spinner";
  import { ApiError } from "@/lib/api";

  export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const login = useMutation({
      mutationFn: async () => {
        // OAuth2 password flow: form-urlencoded, field username (không phải email)
        const body = new URLSearchParams({ username, password });
        const res = await fetch("/api/auth/token", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body,
        });
        if (!res.ok) throw await ApiError.from(res);
        return res.json();
      },
      onSuccess: async () => {
        router.replace("/feedbacks");
        router.refresh();
      },
    });

    const errMsg =
      login.error instanceof ApiError && login.error.status === 401
        ? "Email hoặc mật khẩu sai."
        : String((login.error as ApiError | null)?.message ?? "");

    return (
      <main className="flex min-h-svh items-center justify-center p-6">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Happynest</CardTitle>
            <CardDescription>Đăng nhập để tiếp tục</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                login.mutate();
              }}
            >
              <FieldGroup>
                <Field data-invalid={errMsg ? true : undefined}>
                  <FieldLabel htmlFor="username">Email</FieldLabel>
                  <Input
                    id="username"
                    type="email"
                    autoComplete="username"
                    required
                    aria-invalid={errMsg ? true : undefined}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </Field>
                <Field data-invalid={errMsg ? true : undefined}>
                  <FieldLabel htmlFor="password">Mật khẩu</FieldLabel>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    aria-invalid={errMsg ? true : undefined}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
              </FieldGroup>
              {errMsg ? (
                <Alert variant="destructive">
                  <AlertTitle>Đăng nhập thất bại</AlertTitle>
                  <AlertDescription>{errMsg}</AlertDescription>
                </Alert>
              ) : null}
              <Button type="submit" disabled={login.isPending}>
                {login.isPending ? <Spinner data-icon="inline-start" /> : null}
                Đăng nhập
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    );
  }
  ```
- [ ] **Step 3: Verify thủ công** (backend đang chạy, seed users theo AGENTS):
  - Sai mật khẩu → Alert destructive, không chuyển trang.
  - Đúng (`pm@thesis.local`) → redirect `/feedbacks` (trang placeholder Task 4); DevTools Application → Cookies thấy `access_token` **httpOnly trên localhost:3000**.
  - Cookie còn mà gõ lại `/login` → bị middleware đá về `/feedbacks`.
- [ ] **Step 4: Commit** — `feat(frontend): login page via oauth2 form flow`

### Task 4: Shell (app) + trang placeholder

**Files:** Create: `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/(app)/dashboard/page.tsx`, `…/feedbacks/page.tsx`, `…/analysis/page.tsx`, `…/clusters/page.tsx`, `…/insights/page.tsx`, `…/reports/page.tsx` · Add: `pnpm dlx shadcn@latest add sidebar dropdown-menu avatar badge separator empty skeleton`

- [ ] **Step 1: Shell**
  ```tsx
  "use client";
  import Link from "next/link";
  import {
    Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent,
    SidebarGroupLabel, SidebarHeader, SidebarInset, SidebarMenu,
    SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger,
  } from "@/components/ui/sidebar";
  import { Avatar, AvatarFallback } from "@/components/ui/avatar";
  import { Badge } from "@/components/ui/badge";
  import { Separator } from "@/components/ui/separator";
  import { useMe } from "@/hooks/use-me";
  import {
    LayoutDashboard, MessageSquareText, Activity, Layers, Lightbulb, FileBarChart,
  } from "lucide-react";

  const NAV = [
    { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
    { href: "/feedbacks", label: "Phản hồi", icon: MessageSquareText },
    { href: "/analysis", label: "Analysis", icon: Activity },
    { href: "/clusters", label: "Clusters", icon: Layers },
    { href: "/insights", label: "Insights", icon: Lightbulb },
    { href: "/reports", label: "Báo cáo", icon: FileBarChart },
  ];

  const PHASE_LABEL: Record<string, string> = {
    "/clusters": "Pha P3", "/insights": "Pha P4", "/reports": "Pha P4",
  };

  export default function AppLayout({ children }: { children: React.ReactNode }) {
    const me = useMe();
    const initials = (me.data?.email ?? "?").slice(0, 2).toUpperCase();

    return (
      <SidebarProvider>
        <Sidebar>
          <SidebarHeader className="px-4 py-3 font-heading text-lg">Happynest</SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Menu</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {NAV.map(({ href, label, icon: Icon }) => (
                    <SidebarMenuItem key={href}>
                      <SidebarMenuButton asChild>
                        <Link href={href}>
                          <Icon data-icon="inline-start" />
                          {label}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter className="p-3">
            <div className="flex items-center gap-2">
              <Avatar className="size-8">
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{me.data?.email ?? "…"}</p>
              </div>
              {me.data ? (
                <Badge variant="secondary">{me.data.role}</Badge>
              ) : null}
            </div>
          </SidebarFooter>
        </Sidebar>
        <SidebarInset>
          <header className="flex h-14 items-center gap-2 px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-6" />
            <span className="text-sm text-muted-foreground">
              AI Feedback Agent — bản demo luận văn
            </span>
          </header>
          <main className="flex-1 p-4 md:p-6">{children}</main>
        </SidebarInset>
      </SidebarProvider>
    );
  }
  ```
  > Ghi chú: `PHASE_LABEL` giữ cho UF-02 quyết định cách hiện nhãn pha trên nav; nếu UF không yêu cầu thì bỏ ở lần dọn đầu P5.
- [ ] **Step 2: Placeholder pages** — mẫu đầy đủ (`(app)/dashboard/page.tsx`):
  ```tsx
  import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

  export default function DashboardPage() {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Tổng quan</EmptyTitle>
          <EmptyDescription>Sắp có sau pha P4 — dashboard PM với chart thật.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  ```
  Các file còn lại lặp đúng cấu trúc trên, chỉ khác chuỗi:
  | File | Title | Description |
  |---|---|---|
  | `(app)/feedbacks/page.tsx` | Phản hồi | Sắp có sau FE-03 (list, filter, import CSV). |
  | `(app)/analysis/page.tsx` | Analysis runs | Sắp có sau FE-04 (trigger run, tiến độ, kết quả). |
  | `(app)/clusters/page.tsx` | Clusters | Sắp có sau pha P3. |
  | `(app)/insights/page.tsx` | Insights | Sắp có sau pha P4. |
  | `(app)/reports/page.tsx` | Báo cáo | Sắp có sau pha P4. |
- [ ] **Step 3: Verify** — `pnpm build` xanh; login xong click hết 6 mục menu không 404; role badge hiện đúng (`pm` vs `operations` theo tài khoản thử).
- [ ] **Step 4: Commit** — `feat(frontend): app shell with sidebar nav + phase placeholders`

## Acceptance criteria

- [ ] Chưa login → mọi route (trừ `/login`, `/api`) bị redirect về `/login`; login xong vào được shell
- [ ] Cookie httpOnly nằm trên origin :3000 (không cần CORS, backend không đổi)
- [ ] Lỗi sai thông tin hiện Alert chung; loading state nút dùng Spinner+disabled
- [ ] `pnpm build` xanh; 6 route điều hướng được, không 404
- [ ] Evidence: screenshot trang login lỗi + shell sau login (cho báo cáo UI)

## Limitation ghi nhận v1

Không có logout (cookie httpOnly không xoá được từ client, API chưa có endpoint — contracts §Non-goals). Session hết hạn theo tuổi thọ token. Nếu owner muốn, thêm `POST /api/auth/logout` ở một plan BE sau kèm entry decisions.md.

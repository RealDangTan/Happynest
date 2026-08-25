# FE-03 — Feedback screens (list + filter URL params · create/import · detail + similar)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng checkbox.
>
> **Goal:** Trang `/feedbacks` vận hành thật trên API đã ship: bảng danh sách lọc/pagination bằng URL params, dialog thêm thủ công + import CSV, trang chi tiết kèm panel similar.
>
> **Architecture:** Client components + TanStack Query; filter/page là URL search params (nguồn sự thật); mọi call qua wrapper `lib/api.ts`; mutation xong invalidate query key.
>
> **Tech Stack:** shadcn: table, select, dialog, tabs, textarea, badge (có), skeleton (có), sonner · next/navigation `useSearchParams`.
>
> **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §4 · **API thật (verify 2026-08-25, `backend/app/api/routes/feedback.py` + `schemas/feedback.py`):**
> - `GET /api/feedbacks?limit(≤100,def20)&offset&review_status&severity&category(str)` → `{total, limit, offset, items[FeedbackOut]}` — **KHÔNG có filter `source`** (api-notes sai, bám code)
> - `POST /api/feedbacks` `{source, content, external_ref?, created_at?}` → 201 FeedbackOut
> - `POST /api/feedbacks/import-csv` multipart → `{imported, failed, errors:[{row, reason}]}`
> - `GET /api/feedbacks/{id}?include_raw=bool` → FeedbackDetailOut; `/similar?k(1–50)` → `[…FeedbackOut, score]`, 409 nếu chưa có embedding
> - `FeedbackOut`: id, source, external_ref|null, created_at, imported_at, review_status, pii_detected, severity|null, categories[]|null, ai_issue|null, sentiment|null, confidence|null, requires_human_review, sanitized_content|null

## Global Constraints

- Không Docker; commit nhỏ conventional + `Assisted-by: claude-code`; chỉ đụng `frontend/` + file `FE-*`.
- **PII boundary:** UI KHÔNG gọi `include_raw=true` — chỉ hiển thị `sanitized_content` (+ badge `pii_detected`). Raw ở lại trong DB.
- Filter/page đổi → reset về page 1; URL là nguồn sự thật (share/copy link giữ nguyên trạng thái).
- Windows: dev server chạy nền; verify bằng curl/build từ shell khác.

---

### Task 1: Kiểu dữ liệu + hooks data layer

**Files:** Create: `frontend/lib/types.ts`, `frontend/lib/format.ts`, `frontend/hooks/use-feedbacks.ts`, `frontend/hooks/use-feedback-detail.ts`

- [ ] **Step 1: `lib/types.ts`** — mirror đúng FeedbackOut + enums backend:
  ```ts
  export type Severity = "low" | "medium" | "high" | "critical";
  export type ReviewStatus = "unreviewed" | "pending" | "approved" | "edited" | "rejected";
  export type AiIssue =
    | "hallucination" | "inaccuracy" | "bias"
    | "safety" | "privacy" | "performance" | "other";
  export type Sentiment = "positive" | "negative" | "neutral" | "mixed";

  export type Feedback = {
    id: string;
    source: string;
    external_ref: string | null;
    created_at: string;
    imported_at: string;
    review_status: ReviewStatus;
    pii_detected: boolean;
    severity: Severity | null;
    categories: string[] | null;
    ai_issue: AiIssue | null;
    sentiment: Sentiment | null;
    confidence: number | null;
    requires_human_review: boolean;
    sanitized_content: string | null;
  };

  export type FeedbackListResponse = {
    total: number;
    limit: number;
    offset: number;
    items: Feedback[];
  };

  export type ImportCsvResult = {
    imported: number;
    failed: number;
    errors: { row: number; reason: string }[];
  };
  ```
- [ ] **Step 2: `lib/format.ts`** — helper hiển thị dùng chung:
  ```ts
  const dtf = new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });

  export function formatDate(iso: string): string {
    return dtf.format(new Date(iso));
  }
  ```
- [ ] **Step 3: `hooks/use-feedbacks.ts`** — danh sách theo bộ lọc:
  ```ts
  "use client";
  import { useQuery, keepPreviousData } from "@tanstack/react-query";
  import { apiFetch } from "@/lib/api";
  import type { FeedbackListResponse } from "@/lib/types";

  export type FeedbackListParams = {
    page: number;
    reviewStatus?: string;
    severity?: string;
    category?: string;
  };

  const PAGE_SIZE = 20;

  function toQuery(p: FeedbackListParams): string {
    const q = new URLSearchParams();
    q.set("limit", String(PAGE_SIZE));
    q.set("offset", String((p.page - 1) * PAGE_SIZE));
    if (p.reviewStatus) q.set("review_status", p.reviewStatus);
    if (p.severity) q.set("severity", p.severity);
    if (p.category) q.set("category", p.category);
    return q.toString();
  }

  export function useFeedbacks(params: FeedbackListParams) {
    return useQuery({
      queryKey: ["feedbacks", params],
      queryFn: () =>
        apiFetch<FeedbackListResponse>(`/api/feedbacks?${toQuery(params)}`),
      placeholderData: keepPreviousData,
      staleTime: 30_000,
    });
  }

  export { PAGE_SIZE as FEEDBACKS_PAGE_SIZE };
  ```
- [ ] **Step 4: `hooks/use-feedback-detail.ts`** — detail + similar (409 similar → trả mảng rỗng để UI hiện Empty, không coi là lỗi):
  ```ts
  "use client";
  import { useQuery } from "@tanstack/react-query";
  import { apiFetch, ApiError } from "@/lib/api";
  import type { Feedback } from "@/lib/types";

  export function useFeedbackDetail(id: string) {
    return useQuery({
      queryKey: ["feedback", id],
      queryFn: () => apiFetch<Feedback>(`/api/feedbacks/${id}`),
      staleTime: 60_000,
    });
  }

  export function useSimilarFeedbacks(id: string) {
    return useQuery({
      queryKey: ["similar", id],
      queryFn: async () => {
        try {
          return await apiFetch<(Feedback & { score: number })[]>(
            `/api/feedbacks/${id}/similar?k=5`,
          );
        } catch (e) {
          // 409 = row chưa có embedding (chưa chạy analysis) — không phải lỗi UI
          if (e instanceof ApiError && e.status === 409) return [];
          throw e;
        }
      },
      staleTime: 60_000,
    });
  }
  ```
- [ ] **Step 5: Verify + commit** — `pnpm build` xanh (chưa dùng đâu nhưng type-check được). Commit: `feat(frontend): feedback types + data hooks`

### Task 2: Bảng danh sách + filter/pagination URL params

**Files:** Modify: `frontend/app/(app)/feedbacks/page.tsx` (thay placeholder) · Add components: `pnpm dlx shadcn@latest add table select skeleton`(có)

- [ ] **Step 1: Add components** — `pnpm dlx shadcn@latest add table select`
- [ ] **Step 2: Thay trang** — `useSearchParams` cần bọc `<Suspense>` để build tĩnh không lỗi:
  ```tsx
  "use client";
  import { Suspense } from "react";
  import Link from "next/link";
  import { useRouter, useSearchParams } from "next/navigation";
  import { useFeedbacks, FEEDBACKS_PAGE_SIZE } from "@/hooks/use-feedbacks";
  import type { Feedback } from "@/lib/types";
  import { formatDate } from "@/lib/format";
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
  import { Badge } from "@/components/ui/badge";
  import { Button } from "@/components/ui/button";
  import { Input } from "@/components/ui/input";
  import { Skeleton } from "@/components/ui/skeleton";
  import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

  const SEVERITY_LABEL: Record<string, string> = {
    low: "Thấp", medium: "Trung bình", high: "Cao", critical: "Nghiêm trọng",
  };
  const REVIEW_LABEL: Record<string, string> = {
    unreviewed: "Chưa duyệt", pending: "Chờ duyệt",
    approved: "Đã duyệt", edited: "Đã sửa", rejected: "Đã loại",
  };

  function FeedbacksTable() {
    const router = useRouter();
    const sp = useSearchParams();
    const page = Math.max(1, Number(sp.get("page") ?? "1") || 1);
    const filters = {
      page,
      reviewStatus: sp.get("review_status") ?? undefined,
      severity: sp.get("severity") ?? undefined,
      category: sp.get("category") ?? undefined,
    };
    const { data, isPending, isError, error } = useFeedbacks(filters);

    function setParam(key: string, value: string | null) {
      const next = new URLSearchParams(sp.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.delete("page"); // đổi lọc → về trang 1
      router.replace(`/feedbacks?${next.toString()}`);
    }

    const total = data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(total / FEEDBACKS_PAGE_SIZE));

    if (isPending)
      return (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      );
    if (isError)
      return (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Không tải được dữ liệu</EmptyTitle>
            <EmptyDescription>{error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      );

    return (
      <div className="flex flex-col gap-4">
        {/* Bộ lọc */}
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={sp.get("severity") ?? "all"}
            onValueChange={(v) => setParam("severity", v === "all" ? null : v)}
          >
            <SelectTrigger className="w-44"><SelectValue placeholder="Mức độ" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi mức độ</SelectItem>
              {Object.entries(SEVERITY_LABEL).map(([v, l]) => (
                <SelectItem key={v} value={v}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={sp.get("review_status") ?? "all"}
            onValueChange={(v) => setParam("review_status", v === "all" ? null : v)}
          >
            <SelectTrigger className="w-44"><SelectValue placeholder="Trạng thái" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi trạng thái</SelectItem>
              {Object.entries(REVIEW_LABEL).map(([v, l]) => (
                <SelectItem key={v} value={v}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            placeholder="Lọc theo category…"
            className="w-52"
            defaultValue={sp.get("category") ?? ""}
            onBlur={(e) => setParam("category", e.target.value.trim() || null)}
          />
        </div>

        {data.items.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>Chưa có phản hồi nào</EmptyTitle>
              <EmptyDescription>Nhập dữ liệu bằng nút bên trên hoặc bỏ bộ lọc.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[45%]">Nội dung</TableHead>
                  <TableHead>Nguồn</TableHead>
                  <TableHead>Ngày tạo</TableHead>
                  <TableHead>Mức độ</TableHead>
                  <TableHead>Duyệt</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((fb: Feedback) => (
                  <TableRow key={fb.id} className="cursor-pointer">
                    <TableCell className="max-w-md">
                      <Link href={`/feedbacks/${fb.id}`} className="block">
                        <span className="line-clamp-2">{fb.sanitized_content ?? "(trống)"}</span>
                        {fb.pii_detected ? (
                          <Badge variant="outline" className="mt-1">PII</Badge>
                        ) : null}
                      </Link>
                    </TableCell>
                    <TableCell>{fb.source}</TableCell>
                    <TableCell className="whitespace-nowrap">{formatDate(fb.created_at)}</TableCell>
                    <TableCell>
                      {fb.severity ? (
                        <Badge variant={fb.severity === "critical" || fb.severity === "high" ? "destructive" : "secondary"}>
                          {SEVERITY_LABEL[fb.severity]}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{REVIEW_LABEL[fb.review_status]}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {total} phản hồi · trang {page}/{totalPages}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1}
                  onClick={() => setParam("page", String(page - 1))}>
                  Trước
                </Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages}
                  onClick={() => setParam("page", String(page + 1))}>
                  Sau
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  export default function FeedbacksPage() {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="font-heading text-2xl">Phản hồi</h1>
        <Suspense fallback={<Skeleton className="h-64 w-full" />}>
          <FeedbacksTable />
        </Suspense>
      </div>
    );
  }
  ```
  > Nút "Thêm thủ công" và "Import CSV" gắn vào trang này ở Task 3.
- [ ] **Step 3: Verify** — `pnpm build` xanh; dev server: `curl -s -H "Cookie: access_token=$TOKEN" -o /dev/null -w "%{http_code}" http://localhost:3000/feedbacks` kỳ vọng 200; mở browser kiểm bảng hiện 22 feedback demo, đổi filter thấy URL đổi và bảng refetch.
- [ ] **Step 4: Commit** — `feat(frontend): feedback list with url-param filters + pagination`

### Task 3: Nhập dữ liệu — dialog thêm thủ công + import CSV

**Files:** Create: `frontend/app/(app)/feedbacks/data-entry-dialog.tsx` · Modify: `page.tsx` (gắn nút) · `app/layout.tsx` (Toaster) · Add: `pnpm dlx shadcn@latest add dialog textarea sonner`

- [ ] **Step 1: Add components + mount Toaster** — trong `app/layout.tsx` (client-safe, đặt cạnh Providers):
  ```tsx
  import { Toaster } from "@/components/ui/sonner";
  // … trong <body>, sau </Providers>? — đặt TRONG body, ngoài Providers cũng được:
  //   <Providers>…</Providers>
  //   <Toaster richColors position="top-right" />
  ```
- [ ] **Step 2: `data-entry-dialog.tsx`** — một Dialog, hai Tab:
  ```tsx
  "use client";
  import { useRef, useState } from "react";
  import { useRouter } from "next/navigation";
  import { useMutation, useQueryClient } from "@tanstack/react-query";
  import { toast } from "sonner";
  import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
  import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
  import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
  import { Input } from "@/components/ui/input";
  import { Textarea } from "@/components/ui/textarea";
  import { Button } from "@/components/ui/button";
  import { Spinner } from "@/components/ui/spinner";
  import { apiFetch, ApiError } from "@/lib/api";
  import type { Feedback, ImportCsvResult } from "@/lib/types";

  export function DataEntryDialog() {
    const router = useRouter();
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    function refreshList() {
      void qc.invalidateQueries({ queryKey: ["feedbacks"] });
      router.refresh();
    }

    const createOne = useMutation({
      mutationFn: (body: { source: string; content: string; external_ref?: string }) =>
        apiFetch<Feedback>("/api/feedbacks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
      onSuccess: () => {
        toast.success("Đã thêm phản hồi.");
        setOpen(false);
        refreshList();
      },
      onError: (e) => toast.error(e instanceof ApiError ? e.message : "Lỗi không rõ"),
    });

    const importCsv = useMutation({
      mutationFn: async (file: File) => {
        const fd = new FormData();
        fd.append("file", file);
        // KHÔNG set Content-Type tay — trình duyệt tự thêm boundary multipart
        return apiFetch<ImportCsvResult>("/api/feedbacks/import-csv", {
          method: "POST",
          body: fd,
        });
      },
      onSuccess: (r) => {
        toast.success(`Import xong: ${r.imported} dòng mới, ${r.failed} lỗi.`);
        refreshList();
      },
      onError: (e) => toast.error(e instanceof ApiError ? e.message : "Lỗi không rõ"),
    });

    return (
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button>
            Thêm dữ liệu
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Thêm phản hồi</DialogTitle>
            <DialogDescription>Nhập từng dòng hoặc import cả file CSV.</DialogDescription>
          </DialogHeader>
          <Tabs defaultValue="manual">
            <TabsList>
              <TabsTrigger value="manual">Thủ công</TabsTrigger>
              <TabsTrigger value="csv">Import CSV</TabsTrigger>
            </TabsList>

            <TabsContent value="manual">
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  createOne.mutate({
                    source: String(f.get("source") ?? "").trim(),
                    content: String(f.get("content") ?? "").trim(),
                    external_ref: String(f.get("external_ref") ?? "").trim() || undefined,
                  });
                }}
              >
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="source">Nguồn *</FieldLabel>
                    <Input id="source" name="source" required placeholder="app_store, survey…" />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="external_ref">Tham chiếu ngoài (tuỳ chọn)</FieldLabel>
                    <Input id="external_ref" name="external_ref" placeholder="review#123" />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="content">Nội dung *</FieldLabel>
                    <Textarea id="content" name="content" required rows={4} />
                  </Field>
                </FieldGroup>
                <Button type="submit" disabled={createOne.isPending}>
                  {createOne.isPending ? <Spinner data-icon="inline-start" /> : null}
                  Lưu
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="csv">
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  const file = fileRef.current?.files?.[0];
                  if (file) importCsv.mutate(file);
                }}
              >
                <Field>
                  <FieldLabel htmlFor="csv-file">File CSV *</FieldLabel>
                  <Input ref={fileRef} id="csv-file" type="file" accept=".csv,text/csv" required />
                </Field>
                <p className="text-sm text-muted-foreground">
                  Cột: <code>source,content[,external_ref][,created_at]</code>. Dòng lỗi không chặn dòng hợp lệ.
                </p>
                {importCsv.data ? (
                  <div className="rounded-md border p-3 text-sm">
                    <p>Đã nhập: <b>{importCsv.data.imported}</b> · Lỗi: <b>{importCsv.data.failed}</b></p>
                    {importCsv.data.errors.length > 0 ? (
                      <ul className="mt-2 max-h-32 overflow-auto text-muted-foreground">
                        {importCsv.data.errors.map((er) => (
                          <li key={er.row}>Dòng {er.row}: {er.reason}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                <Button type="submit" disabled={importCsv.isPending}>
                  {importCsv.isPending ? <Spinner data-icon="inline-start" /> : null}
                  Import
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    );
  }
  ```
  > `fileRef` đã khai báo đầu component.
- [ ] **Step 3: Gắn nút vào trang** — trong `page.tsx` (component `FeedbacksPage`), hàng tiêu đề:
  ```tsx
  import { DataEntryDialog } from "./data-entry-dialog";
  // …
  <div className="flex items-center justify-between">
    <h1 className="font-heading text-2xl">Phản hồi</h1>
    <DataEntryDialog />
  </div>
  ```
- [ ] **Step 4: Verify** — `pnpm build` xanh; qua browser: thêm 1 feedback mới → toast + bảng refetch có dòng mới; import file CSV thử nghiệm (tạo `tmp-test.csv` 3 dòng hợp lệ + 1 dòng thiếu content) → toast tổng kết đúng `{imported, failed}`, danh sách lỗi hiển thị số dòng; kiểm `pii_detected` badge với nội dung chứa SĐT.
- [ ] **Step 5: Commit** — `feat(frontend): feedback data entry (manual form + csv import dialog)`

### Task 4: Trang chi tiết + panel similar

**Files:** Create: `frontend/app/(app)/feedbacks/[id]/page.tsx`

- [ ] **Step 1: Trang chi tiết**:
  ```tsx
  "use client";
  import Link from "next/link";
  import { useParams } from "next/navigation";
  import { useFeedbackDetail, useSimilarFeedbacks } from "@/hooks/use-feedback-detail";
  import { formatDate } from "@/lib/format";
  import { Badge } from "@/components/ui/badge";
  import { Button } from "@/components/ui/button";
  import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
  import { Separator } from "@/components/ui/separator";
  import { Skeleton } from "@/components/ui/skeleton";
  import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

  const SEVERITY_LABEL: Record<string, string> = {
    low: "Thấp", medium: "Trung bình", high: "Cao", critical: "Nghiêm trọng",
  };
  const REVIEW_LABEL: Record<string, string> = {
    unreviewed: "Chưa duyệt", pending: "Chờ duyệt",
    approved: "Đã duyệt", edited: "Đã sửa", rejected: "Đã loại",
  };

  export default function FeedbackDetailPage() {
    const { id } = useParams<{ id: string }>();
    const fb = useFeedbackDetail(id);
    const similar = useSimilarFeedbacks(id);

    if (fb.isPending)
      return (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-40 w-full" />
        </div>
      );
    if (fb.isError)
      return (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>{fb.error.status === 404 ? "Không tìm thấy phản hồi" : "Không tải được"}</EmptyTitle>
            <EmptyDescription>{fb.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      );

    const d = fb.data;
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link href="/feedbacks">← Danh sách</Link>
          </Button>
        </div>
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>Phản hồi · {d.source}</CardTitle>
              {d.severity ? <Badge variant={d.severity === "critical" || d.severity === "high" ? "destructive" : "secondary"}>{SEVERITY_LABEL[d.severity]}</Badge> : null}
              <Badge variant="outline">{REVIEW_LABEL[d.review_status]}</Badge>
              {d.pii_detected ? <Badge variant="outline">Phát hiện PII</Badge> : null}
            </div>
            <CardDescription>
              {formatDate(d.created_at)}
              {d.external_ref ? ` · ${d.external_ref}` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {d.sanitized_content ?? "(nội dung trống)"}
            </p>
            <Separator />
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm sm:grid-cols-[10rem_1fr]">
              <dt className="text-muted-foreground">AI issue</dt>
              <dd>{d.ai_issue ?? "—"}</dd>
              <dt className="text-muted-foreground">Sentiment</dt>
              <dd>{d.sentiment ?? "—"}</dd>
              <dt className="text-muted-foreground">Confidence</dt>
              <dd>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : "—"}</dd>
              <dt className="text-muted-foreground">Categories</dt>
              <dd className="flex flex-wrap gap-1">
                {(d.categories ?? []).length > 0
                  ? d.categories!.map((c) => <Badge key={c} variant="secondary">{c}</Badge>)
                  : "—"}
              </dd>
              <dt className="text-muted-foreground">Cần người duyệt</dt>
              <dd>{d.requires_human_review ? "Có" : "Không"}</dd>
            </dl>
          </CardContent>
        </Card>

        <section className="flex flex-col gap-3">
          <h2 className="font-heading text-lg">Phản hồi tương tự</h2>
          {similar.isPending ? (
            <Skeleton className="h-24 w-full" />
          ) : (similar.data?.length ?? 0) === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>Chưa có dữ liệu tương tự</EmptyTitle>
                <EmptyDescription>Chạy Analysis để tạo embedding cho phản hồi này.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {similar.data!.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/feedbacks/${s.id}`}
                    className="flex items-start justify-between gap-4 rounded-lg border p-3 hover:bg-accent"
                  >
                    <span className="line-clamp-2 flex-1 text-sm">{s.sanitized_content}</span>
                    <Badge variant="secondary">{Math.round(s.score * 100)}%</Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  }
  ```
- [ ] **Step 2: Verify** — `pnpm build` xanh; browser: click 1 dòng từ bảng → trang chi tiết đúng nội dung/badge; mục similar hiện danh sách (hoặc Empty nếu row chưa có embedding — đúng 409 đã xử lý); link similar điều hướng chéo được.
- [ ] **Step 3: Commit** — `feat(frontend): feedback detail page with similar panel`

## Acceptance criteria

- [ ] `/feedbacks`: bảng 22 feedback demo; filter severity/review_status/category + pagination đều hoạt động và **sống trong URL** (copy link giữ nguyên trạng thái); đổi filter luôn về trang 1
- [ ] Thêm thủ công → 201, toast, bảng refetch ngay; Import CSV → tổng kết `{imported, failed}` + danh sách lỗi theo dòng
- [ ] Chi tiết: đủ nhãn (ai_issue, sentiment, confidence, categories, requires_human_review); similar hiện kèm % độ giống; 409 chưa-embedding hiện Empty thay vì lỗi
- [ ] **PII boundary:** toàn UI không hề gọi `include_raw=true` (grep xác nhận); chỉ hiển thị `sanitized_content`
- [ ] `pnpm build` xanh sau mỗi task; mỗi task ≥ 1 commit
- [ ] Evidence luận văn: screenshot bảng + filter URL, dialog import kết quả, trang chi tiết + similar

## Non-goals (ghi rõ tránh scope creep)

- Không sửa/xoá feedback (API không có); không duyệt HITL tại đây (P2/FE-05); không filter theo nguồn (API chưa hỗ trợ — api-notes ghi thừa); không hiển thị raw_content.

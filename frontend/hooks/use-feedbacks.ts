"use client";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  Feedback,
  FeedbackFacets,
  FeedbackListResponse,
} from "@/lib/types";
import type { FeedbackServerSort } from "@/lib/table-sorts";

export type FeedbackListParams = {
  page: number;
  /** Số dòng/trang — backend cap 100 */
  pageSize?: number;
  /** Faceted multi-select: ['high','critical'] → severity=high,critical */
  severity?: string[];
  sentiment?: string[];
  /** Một slug hoặc nhiều (khớp BẤT KỲ — feedback mang tới 3 chủ đề). */
  topic?: string | string[];
  source?: string;
  /** Search text toàn cục (backend: feedback_text + source, ILIKE) */
  q?: string;
  sort?: FeedbackServerSort;
  importId?: string;
  /** Giới hạn trong một product; bỏ trống = mọi product của tài khoản. */
  productId?: string;
  analysisState?: "pending" | "completed" | "uncategorized";
};

const DEFAULT_PAGE_SIZE = 20;

function toQuery(p: FeedbackListParams): string {
  const q = new URLSearchParams();
  q.set("limit", String(p.pageSize ?? DEFAULT_PAGE_SIZE));
  q.set("offset", String((p.page - 1) * (p.pageSize ?? DEFAULT_PAGE_SIZE)));
  if (p.severity?.length) q.set("severity", p.severity.join(","));
  if (p.sentiment?.length) q.set("sentiment", p.sentiment.join(","));
  const topics = Array.isArray(p.topic) ? p.topic : p.topic ? [p.topic] : [];
  if (topics.length) q.set("topic", topics.join(","));
  if (p.source) q.set("source", p.source);
  if (p.q) q.set("q", p.q);
  if (p.sort) q.set("sort", p.sort);
  if (p.importId) q.set("import_id", p.importId);
  if (p.productId) q.set("product_id", p.productId);
  if (p.analysisState) q.set("analysis_state", p.analysisState);
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

/**
 * Chủ đề và khoá metadata THỰC SỰ có trong phạm vi (product + tuỳ chọn một lô
 * nhập) — dựng bộ lọc chủ đề và menu cột metadata của vault. Nằm dưới khoá
 * ["feedbacks", …] nên mọi thao tác sửa/xoá/phân loại làm mới nó theo.
 */
export function useFeedbackFacets(params: {
  productId: string | null | undefined;
  importId?: string | null;
}) {
  return useQuery({
    queryKey: ["feedbacks", "facets", params.productId, params.importId ?? null],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.productId) q.set("product_id", params.productId);
      if (params.importId) q.set("import_id", params.importId);
      return apiFetch<FeedbackFacets>(`/api/feedbacks/facets?${q.toString()}`);
    },
    enabled: params.productId != null,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    retry: false,
  });
}

export type FeedbackUpdateIn = {
  feedback_text?: string;
  source?: string;
  occurred_at?: string;
  ai_analysis?: {
    severity?: string;
    sentiment?: string;
    topics?: string[];
    emotions?: string[];
    intent?: string;
  };
};

function invalidateFeedbacks(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["feedbacks"] });
  void qc.invalidateQueries({ queryKey: ["similar"] });
}

/** PATCH /api/feedbacks/{id} (pm) — text re-sanitized server-side. */
export function useUpdateFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: FeedbackUpdateIn }) =>
      apiFetch<Feedback>(`/api/feedbacks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["feedback", updated.id], updated);
      invalidateFeedbacks(qc);
    },
  });
}

/** DELETE /api/feedbacks/{id} (pm) — hard delete. */
export function useDeleteFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/feedbacks/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateFeedbacks(qc),
  });
}

/** POST /api/feedbacks/bulk-delete (pm) — hard delete một lượt. */
export function useBulkDeleteFeedbacks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) =>
      apiFetch<{ deleted: number }>("/api/feedbacks/bulk-delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      }),
    onSuccess: () => invalidateFeedbacks(qc),
  });
}

/** DELETE /api/imports/{id} (pm) — xoá lô + toàn bộ feedback/runs của lô. */
export function useDeleteImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/imports/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["imports"] });
      invalidateFeedbacks(qc);
    },
  });
}

export { DEFAULT_PAGE_SIZE as FEEDBACKS_PAGE_SIZE };

"use client";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Feedback, FeedbackListResponse } from "@/lib/types";

export type FeedbackListParams = {
  page: number;
  severity?: string;
  sentiment?: string;
  topic?: string;
  source?: string;
  importId?: string;
  analysisState?: "pending" | "completed";
};

const PAGE_SIZE = 20;

function toQuery(p: FeedbackListParams): string {
  const q = new URLSearchParams();
  q.set("limit", String(PAGE_SIZE));
  q.set("offset", String((p.page - 1) * PAGE_SIZE));
  if (p.severity) q.set("severity", p.severity);
  if (p.sentiment) q.set("sentiment", p.sentiment);
  if (p.topic) q.set("topic", p.topic);
  if (p.source) q.set("source", p.source);
  if (p.importId) q.set("import_id", p.importId);
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

export type FeedbackUpdateIn = {
  feedback_text?: string;
  source?: string;
  occurred_at?: string;
  ai_analysis?: { severity?: string; sentiment?: string; topics?: string[] };
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

export { PAGE_SIZE as FEEDBACKS_PAGE_SIZE };

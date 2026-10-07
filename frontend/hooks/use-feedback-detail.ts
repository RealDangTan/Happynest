"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api";
import type { Feedback } from "@/lib/types";

export type SimilarFeedback = {
  id: string;
  score: number;
  source: string;
  snippet: string | null;
};

export function useFeedbackDetail(id: string | null) {
  return useQuery({
    queryKey: ["feedback", id],
    queryFn: () => apiFetch<Feedback>(`/api/feedbacks/${id}`),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

export function useSimilarFeedbacks(id: string | null) {
  return useQuery({
    queryKey: ["similar", id],
    queryFn: async () => {
      try {
        return await apiFetch<SimilarFeedback[]>(
          `/api/feedbacks/${id}/similar?k=5`,
        );
      } catch (e) {
        // 409 = row chưa có embedding (chưa chạy analysis) — không phải lỗi UI
        if (e instanceof ApiError && e.status === 409) return [];
        throw e;
      }
    },
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

"use client";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { FeedbackListResponse, RunProgress } from "@/lib/types";

export const RUN_RESULTS_PAGE_SIZE = 20;

/** Progress một run — poll 4s khi còn running, dừng hẳn khi completed/failed. */
export function useRunProgress(runId: string | null) {
  return useQuery({
    queryKey: ["analysis", "run", runId],
    enabled: runId != null,
    queryFn: () =>
      apiFetch<RunProgress>(`/api/analysis/runs/${runId}`),
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 4000 : false,
    staleTime: 0,
  });
}

/** Kết quả của một run (phân trang offset). */
export function useRunResults(runId: string | null, page: number) {
  return useQuery({
    queryKey: ["analysis", "results", runId, page],
    enabled: runId != null,
    placeholderData: keepPreviousData,
    staleTime: 15_000,
    queryFn: () => {
      const qs = new URLSearchParams({
        limit: String(RUN_RESULTS_PAGE_SIZE),
        offset: String((page - 1) * RUN_RESULTS_PAGE_SIZE),
      });
      return apiFetch<FeedbackListResponse>(
        `/api/analysis/runs/${runId}/results?${qs.toString()}`,
      );
    },
  });
}

export function useTriggerRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ run_id: string }>("/api/analysis/runs", { method: "POST" }),
    onSuccess: () =>
      void qc.invalidateQueries({ queryKey: ["analysis"] }),
  });
}

"use client";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  AnalysisCostPreview,
  AnalysisScope,
  FeedbackListResponse,
  RunListResponse,
  RunProgress,
} from "@/lib/types";

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

export function useRuns() {
  return useQuery({
    queryKey: ["analysis", "runs"],
    queryFn: () => apiFetch<RunListResponse>("/api/analysis/runs?limit=50"),
    refetchInterval: 4000,
    staleTime: 0,
  });
}

export function useAnalysisPreview() {
  return useMutation({
    mutationFn: (scope: AnalysisScope) =>
      apiFetch<AnalysisCostPreview>("/api/analysis/runs/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scope),
      }),
  });
}

export function useTriggerRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      scope,
      confirmedItemCount,
    }: {
      scope: AnalysisScope;
      confirmedItemCount: number;
    }) =>
      apiFetch<{ run_id: string }>("/api/analysis/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...scope,
          confirmed_item_count: confirmedItemCount,
        }),
      }),
    onSuccess: () =>
      void qc.invalidateQueries({ queryKey: ["analysis"] }),
  });
}

export function useCancelRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      apiFetch<RunProgress>(`/api/analysis/runs/${runId}/cancel`, { method: "POST" }),
    onSuccess: (_, runId) => {
      void qc.invalidateQueries({ queryKey: ["analysis", "run", runId] });
      void qc.invalidateQueries({ queryKey: ["analysis", "runs"] });
    },
  });
}

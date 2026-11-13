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

/** Run scope cap ở 100 items (receipt) nên 1 lần fetch limit=100 là đủ toàn
 * bộ kết quả — sort/filter/search client-side trung thực trên toàn run. */
export const RUN_RESULTS_PAGE_SIZE = 100;

/** Kết quả của một run — tải hết một lượt (≤100 items). */
export function useRunResults(runId: string | null) {
  return useQuery({
    queryKey: ["analysis", "results", runId],
    enabled: runId != null,
    placeholderData: keepPreviousData,
    staleTime: 15_000,
    queryFn: () => {
      const qs = new URLSearchParams({
        limit: String(RUN_RESULTS_PAGE_SIZE),
        offset: "0",
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
    // Nhịp nhanh chỉ khi có lượt PHÂN LOẠI đang chạy. Trước đây poll 4s vô
    // điều kiện trên mọi trang — tải nền thường trực lên DB xa (QA HN-015).
    // Row của cuộc điều tra AI giữ `running` tới khi được duyệt nên không tính.
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (run) => run.status === "running" && run.import_id != null,
      )
        ? 4000
        : 20_000,
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

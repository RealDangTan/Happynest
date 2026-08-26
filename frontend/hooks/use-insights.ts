"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  InsightsListResponse,
  InsightsRunResult,
} from "@/lib/types";

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => apiFetch<InsightsListResponse>("/api/insights"),
    staleTime: 30_000,
  });
}

/** Sinh insight — replace-all XOÁ insight cũ rồi tạo lại (C6).
 * KHÔNG nuốt error ở đây: caller đọc ApiError.status === 409 để render Alert. */
export function useRunInsights() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<InsightsRunResult>("/api/insights/run", { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["insights"] });
      // run mới đổi số liệu tổng hợp (emerging/priority) của reports + dashboard
      void qc.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

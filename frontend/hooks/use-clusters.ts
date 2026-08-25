"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ClusterItem, ClusterRunResult } from "@/lib/types";

export type ClusterSort = "feedback_count" | "growth_ratio" | "recent";

export function useClusters(sort: ClusterSort) {
  return useQuery({
    queryKey: ["clusters", sort],
    queryFn: () =>
      apiFetch<{ items: ClusterItem[] }>(`/api/clusters?sort=${sort}`),
    staleTime: 30_000,
  });
}

/** Rebuild phân cụm — XOÁ insights + clusters cũ rồi tạo lại (C5). */
export function useRunClustering() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<ClusterRunResult>("/api/clusters/run", { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["clusters"] }),
  });
}

"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { InsightItem, InsightsListResponse } from "@/lib/types";

export function useInsights(productId?: string | null) {
  return useQuery({
    queryKey: productId === undefined ? ["insights"] : ["insights", "product", productId],
    queryFn: () =>
      apiFetch<InsightsListResponse>(
        productId ? "/api/insights?product_id=" + encodeURIComponent(productId) : "/api/insights",
      ),
    enabled: productId !== null,
    staleTime: 0,
  });
}

/** PATCH /api/insights/{id} (pm) — sửa title/finding trực tiếp (pm). */
export function useUpdateInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: { title?: string; finding?: string };
    }) =>
      apiFetch<InsightItem>(`/api/insights/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

/** DELETE /api/insights/{id} (pm) — xoá insight sai (actions cascade). */
export function useDeleteInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/insights/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["insights"] });
      void qc.invalidateQueries({ queryKey: ["agent"] });
    },
  });
}
// Insights giờ do UNDERSTAND agent sinh (Gate #2) — không còn nút "Sinh
// insight" replace-all; FE Understand/Act sẽ nối /api/agent/* ở series sau.

"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useProduct } from "@/hooks/use-product";
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

/** Cụm lại feedback của product đang chọn (C5, theo product từ 2026-11-05 —
 *  không còn gộp feedback của product khác vào cùng cụm). */
export function useRunClustering() {
  const qc = useQueryClient();
  const { productId } = useProduct();
  return useMutation({
    mutationFn: () => {
      if (!productId) throw new Error("Chưa chọn sản phẩm để phân cụm.");
      return apiFetch<ClusterRunResult>("/api/clusters/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId }),
      });
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["clusters"] }),
  });
}

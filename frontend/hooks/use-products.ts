"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ActiveSchemaResponse, Product, ProductListResponse } from "@/lib/types";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => apiFetch<ProductListResponse>("/api/products"),
    staleTime: 60_000,
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      apiFetch<Product>("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["products"] }),
  });
}

/** Settings — rename / re-describe the active product. 409 on duplicate name. */
export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { name?: string; description?: string | null } }) =>
      apiFetch<Product>(`/api/products/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["products"] }),
  });
}

/** Schema ACTIVE của product (null khi chưa bootstrap qua Gate #1 nào). */
export function useActiveSchema(productId: string | null) {
  return useQuery({
    queryKey: ["products", "schema", productId],
    queryFn: () =>
      apiFetch<ActiveSchemaResponse>(`/api/products/${productId}/schema`),
    enabled: productId != null,
    staleTime: 30_000,
  });
}

/** DELETE /api/products/{id} (pm) — cascade toàn bộ feedback/imports/insights. */
export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ product_id: string; deleted_counts: Record<string, number> }>(
        `/api/products/${id}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
      void qc.invalidateQueries({ queryKey: ["feedbacks"] });
      void qc.invalidateQueries({ queryKey: ["imports"] });
      void qc.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}

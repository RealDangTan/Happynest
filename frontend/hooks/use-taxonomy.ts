"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type {
  ReEnrichResponse,
  TaxonomyApplyResponse,
  TaxonomyGenerateRequest,
  TaxonomyGenerateResponse,
  TaxonomyListResponse,
  TaxonomyNode,
  TaxonomyProposal,
  TopicRecommendResponse,
  TopicRecommendation,
} from "@/lib/types";

export function useTaxonomy(productId: string | null) {
  return useQuery({
    queryKey: ["taxonomy", productId],
    queryFn: () =>
      apiFetch<TaxonomyListResponse>(
        `/api/taxonomies?product_id=${productId}`,
      ),
    enabled: productId != null,
    staleTime: 30_000,
  });
}

/** GPT sinh proposal (tốn LLM) — proposal STATELESS. */
export function useGenerateProposal() {
  return useMutation({
    mutationFn: (body: TaxonomyGenerateRequest) =>
      apiFetch<TaxonomyGenerateResponse>("/api/taxonomies/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  });
}

/** Human Gate: apply proposal (đã review/sửa) → Active Taxonomy / v2. */
export function useApplyProposal(productId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (proposal: TaxonomyProposal) =>
      apiFetch<TaxonomyApplyResponse>("/api/taxonomies/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, proposal }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["taxonomy", productId] });
      // version badge đọc từ products — đồng bộ sau khi bump.
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** GPT đề xuất topic từ pool uncategorized — pool rỗng không tốn LLM. */
export function useRecommendTopics() {
  return useMutation({
    mutationFn: (body: { product_id: string; pool_limit?: number }) =>
      apiFetch<TopicRecommendResponse>("/api/taxonomies/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  });
}

/** Human Gate: nhận topic đề xuất → tạo node + bump version. */
export function useApplyRecommendations(productId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (topics: TopicRecommendation[]) =>
      apiFetch<TaxonomyApplyResponse>("/api/taxonomies/recommend/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, topics }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["taxonomy", productId] });
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Human CRUD (owner 2026-10-23): tự tay thêm node vào Active Taxonomy —
 * slug tự sinh phía BE, bump taxonomy_version. `name` = tiếng Anh canonical,
 * `name_vi` = nhãn hiển thị tiếng Việt (bỏ trống → BE fallback `name`). */
export function useCreateTaxonomyNode(productId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      name_vi?: string | null;
      parent_slug?: string | null;
      description?: string | null;
    }) =>
      apiFetch<TaxonomyNode>("/api/taxonomies/nodes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, ...body }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["taxonomy", productId] });
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Human CRUD: đổi tên (EN canonical) / name_vi (hiển thị) / mô tả — slug
 * bất biến (plan 31). `name_vi` undefined = giữ nguyên nhãn hiển thị. */
export function useUpdateTaxonomyNode(productId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      slug,
      name,
      name_vi,
      description,
    }: {
      slug: string;
      name?: string;
      name_vi?: string;
      description?: string | null;
    }) =>
      apiFetch<TaxonomyNode>(`/api/taxonomies/nodes/${encodeURIComponent(slug)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, name, name_vi, description }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["taxonomy", productId] });
    },
  });
}

/** Human CRUD: xóa node lá (còn con → 409 từ BE). Dữ liệu cũ giữ nguyên slug. */
export function useDeleteTaxonomyNode(productId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      apiFetch<void>(`/api/taxonomies/nodes/${encodeURIComponent(slug)}?product_id=${productId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["taxonomy", productId] });
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Vòng taxonomy evolution: clear nhãn rows uncategorized → run Analysis kế
 * tiếp enrich lại theo taxonomy mới. */
export function useReEnrichUncategorized() {
  return useMutation({
    mutationFn: (body: { product_id: string }) =>
      apiFetch<ReEnrichResponse>("/api/analysis/re-enrich-uncategorized", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  });
}

"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  ImportListResponse,
  ImportPreview,
  ImportRecord,
  MappingDecision,
  MappingProposal,
} from "@/lib/types";

/** Free gate: upload CSV → sanitized deterministic profile only. */
export function useCreateImport() {
  return useMutation({
    mutationFn: ({
      file,
      productId,
    }: {
      file: File;
      productId: string;
    }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("product_id", productId);
      return apiFetch<ImportRecord>("/api/imports", {
        method: "POST",
        body: form,
      });
    },
  });
}

export function useImports() {
  return useQuery({
    queryKey: ["imports", "activity"],
    queryFn: () => apiFetch<ImportListResponse>("/api/imports?limit=50"),
    refetchInterval: 4000,
    staleTime: 0,
  });
}

export function useImport(importId: string | null) {
  return useQuery({
    queryKey: ["imports", importId],
    queryFn: () => apiFetch<ImportRecord>(`/api/imports/${importId}`),
    enabled: !!importId,
    refetchInterval: (query) =>
      ["mapping_generating", "importing"].includes(query.state.data?.status ?? "")
        ? 2000
        : false,
  });
}

export function useImportPreview(importId: string | null) {
  return useQuery({
    queryKey: ["imports", importId, "preview"],
    queryFn: () => apiFetch<ImportPreview>(`/api/imports/${importId}/preview`),
    enabled: !!importId,
    staleTime: Infinity,
  });
}

export function useProposeMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (importId: string) =>
      apiFetch<{ import_id: string; status: string }>(
        `/api/imports/${importId}/mapping/proposal`,
        { method: "POST" },
      ),
    onSuccess: (_, importId) => {
      void qc.invalidateQueries({ queryKey: ["imports"] });
      void qc.invalidateQueries({ queryKey: ["imports", importId] });
    },
  });
}

export function useCancelImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (importId: string) =>
      apiFetch<ImportRecord>(`/api/imports/${importId}/cancel`, { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["imports"] }),
  });
}

export function useGetMapping(importId: string | null) {
  return useQuery({
    queryKey: ["import-mapping", importId],
    queryFn: () => apiFetch<MappingProposal>(`/api/imports/${importId}/mapping`),
    enabled: !!importId,
    staleTime: 5 * 60_000,
  });
}

/** Gate #1: human chốt mapping → import thực thi MỘT LẦN. */
export function useDecideMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      importId,
      decisions,
      defaultSource,
    }: {
      importId: string;
      decisions: MappingDecision[];
      defaultSource?: string;
    }) => {
      const q = defaultSource
        ? `?default_source=${encodeURIComponent(defaultSource)}`
        : "";
      return apiFetch<{ import_id: string; status: "importing" }>(
        `/api/imports/${importId}/mapping/decision${q}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decisions }),
        },
      );
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["imports"] }),
  });
}

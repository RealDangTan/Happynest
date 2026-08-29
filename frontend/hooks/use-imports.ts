"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  ImportApplyReport,
  ImportRecord,
  MappingDecision,
  MappingProposal,
} from "@/lib/types";

/** Bước 1 LISTEN: upload CSV → profile → LLM mapping proposal (chờ Gate #1). */
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
      return apiFetch<ImportApplyReport>(
        `/api/imports/${importId}/mapping/decision${q}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decisions }),
        },
      );
    },
  });
}

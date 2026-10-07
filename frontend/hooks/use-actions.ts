"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  ActionItem,
  ActionUpdateInput,
  ActionsListResponse,
  HumanActionInput,
} from "@/lib/types";

/** Portfolio + priority matrix grouping for one report (insight). */
export function useActions(insightId: string | null) {
  return useQuery({
    queryKey: ["actions", insightId],
    enabled: insightId != null,
    queryFn: () =>
      apiFetch<ActionsListResponse>(`/api/insights/${insightId}/actions`),
    staleTime: 15_000,
  });
}

/** LLM routing + estimates — only valid on an approved/edited insight (409 otherwise). */
export function useGenerateActions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (insightId: string) =>
      apiFetch<{
        actions_created: number;
        functions_skipped: string[];
        generation_error: string | null;
      }>(
        `/api/insights/${insightId}/actions/generate`,
        { method: "POST" },
      ),
    onSuccess: (_, insightId) => void qc.invalidateQueries({ queryKey: ["actions", insightId] }),
  });
}

/** Gate #3 — human override; agent scores stay untouched on the backend. */
export function useUpdateAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      actionId,
      body,
    }: {
      actionId: string;
      body: ActionUpdateInput;
    }) =>
      apiFetch<ActionItem>(`/api/actions/${actionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (action) => {
      void qc.invalidateQueries({ queryKey: ["actions", action.insight_id] });
      void qc.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}

/** Human-added action — arrives already accepted. */
export function useAddAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ insightId, body }: { insightId: string; body: HumanActionInput }) =>
      apiFetch<ActionItem>(`/api/insights/${insightId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: (action) => void qc.invalidateQueries({ queryKey: ["actions", action.insight_id] }),
  });
}

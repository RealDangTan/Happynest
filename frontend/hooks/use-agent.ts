"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  AgentDecision,
  AgentRunStatusResponse,
  AgentTraceResponse,
} from "@/lib/types";

/** UNDERSTAND investigation — graph runs in background to the Gate #2 interrupt. */
export function useCreateAgentRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { product_id: string; question: string }) =>
      apiFetch<{ run_id: string }>("/api/agent/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["analysis", "runs"] }),
  });
}

/** Poll while running; stop once the gate decision or a final status lands. */
export function useAgentRun(runId: string | null) {
  return useQuery({
    queryKey: ["agent", "run", runId],
    enabled: runId != null,
    queryFn: () =>
      apiFetch<AgentRunStatusResponse>(`/api/agent/runs/${runId}`),
    refetchInterval: (query) =>
      ["running", "pending_approval", "decision_processing"].includes(query.state.data?.status ?? "")
        ? (query.state.data?.status === "decision_processing" ? 1500 : 3000)
        : false,
    staleTime: 0,
  });
}

/** Live metadata trace (HAX G4) — poll while the investigation runs, then stop. */
export function useAgentTrace(runId: string | null, active: boolean) {
  return useQuery({
    queryKey: ["agent", "run", runId, "trace"],
    enabled: runId != null,
    queryFn: () =>
      apiFetch<AgentTraceResponse>(`/api/agent/runs/${runId}/trace`),
    refetchInterval: active ? 2000 : false,
    staleTime: 0,
  });
}

/** Gate #2 — the final human decision on a finding. */
export function useAgentDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      runId,
      action,
      editedInsight,
      reason,
    }: {
      runId: string;
      action: AgentDecision;
      editedInsight?: { title?: string; finding?: string };
      reason?: string;
    }) =>
      apiFetch<{
        run_id: string;
        final_status: string | null;
        insights_created: string[];
      }>(`/api/agent/runs/${runId}/decision?background=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          edited_insight: editedInsight ?? null,
          reason: reason ?? null,
        }),
      }),
    onSuccess: (_result, variables) => {
      qc.setQueryData<AgentRunStatusResponse>(["agent", "run", variables.runId], old => old ? {
        ...old, status: "decision_processing", error: null,
      } : old);
      void qc.invalidateQueries({ queryKey: ["agent"] });
      void qc.invalidateQueries({ queryKey: ["insights"] });
      void qc.invalidateQueries({ queryKey: ["analysis", "runs"] });
    },
  });
}

"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { InsightsListResponse } from "@/lib/types";

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => apiFetch<InsightsListResponse>("/api/insights"),
    staleTime: 30_000,
  });
}
// Insights giờ do UNDERSTAND agent sinh (Gate #2) — không còn nút "Sinh
// insight" replace-all; FE Understand/Act sẽ nối /api/agent/* ở series sau.

"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ReportSummary } from "@/lib/types";

export type SummaryDays = 7 | 30 | 90;

/** C4 dùng chung /reports và /dashboard — cùng queryKey nên cache share
 * giữa hai trang khi cùng cửa sổ `days` (AC dashboard khớp 1:1). */
export function useReportSummary(days: SummaryDays) {
  return useQuery({
    queryKey: ["reports", "summary", days],
    queryFn: () => apiFetch<ReportSummary>(`/api/reports/summary?days=${days}`),
    staleTime: 60_000,
  });
}

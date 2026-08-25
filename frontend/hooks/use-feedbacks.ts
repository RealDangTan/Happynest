"use client";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { FeedbackListResponse } from "@/lib/types";

export type FeedbackListParams = {
  page: number;
  reviewStatus?: string;
  severity?: string;
  category?: string;
};

const PAGE_SIZE = 20;

function toQuery(p: FeedbackListParams): string {
  const q = new URLSearchParams();
  q.set("limit", String(PAGE_SIZE));
  q.set("offset", String((p.page - 1) * PAGE_SIZE));
  if (p.reviewStatus) q.set("review_status", p.reviewStatus);
  if (p.severity) q.set("severity", p.severity);
  if (p.category) q.set("category", p.category);
  return q.toString();
}

export function useFeedbacks(params: FeedbackListParams) {
  return useQuery({
    queryKey: ["feedbacks", params],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(`/api/feedbacks?${toQuery(params)}`),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}

export { PAGE_SIZE as FEEDBACKS_PAGE_SIZE };

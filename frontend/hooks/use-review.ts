"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CorrectionResponse, Feedback } from "@/lib/types";

export type ReviewAction = "approve" | "edit" | "reject";

export type ReviewBody = {
  action: ReviewAction;
  edited_content?: string;
  reason?: string;
};

/** Feedback gốc chưa che PII — CHỈ toggle review ở trang detail pending được
 * bật query này (ngoại lệ duy nhất của app, decisions 2026-08-26). */
export function useFeedbackRaw(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["feedback-raw", id],
    enabled,
    queryFn: () =>
      apiFetch<Feedback>(`/api/feedbacks/${id}?include_raw=true`),
    staleTime: 0,
  });
}

/** Id item pending kế tiếp sau `id` trong hàng đợi (để offer duyệt tuần tự). */
export function usePendingNeighbors(id: string) {
  return useQuery({
    queryKey: ["pending-neighbors", id],
    queryFn: async () => {
      const list = await apiFetch<{ items: Feedback[] }>(
        "/api/feedbacks?review_status=pending&limit=50",
      );
      const idx = list.items.findIndex((f) => f.id === id);
      if (idx === -1 || idx + 1 >= list.items.length) return null;
      return list.items[idx + 1].id;
    },
    staleTime: 15_000,
  });
}

function useInvalidateReviewTargets() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ["feedback"] });
    void qc.invalidateQueries({ queryKey: ["feedbacks"] });
    void qc.invalidateQueries({ queryKey: ["analysis"] });
    void qc.invalidateQueries({ queryKey: ["pending-neighbors"] });
  };
}

/** Duyệt / sửa / từ chối — resume graph HITL phía BE. */
export function useSubmitReview(id: string) {
  const invalidate = useInvalidateReviewTargets();
  return useMutation({
    mutationFn: (body: ReviewBody) =>
      apiFetch<Feedback>(`/api/reviews/${id}`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

export type CorrectionBody = {
  categories?: string[];
  ai_issue?: string;
  severity?: string;
  sentiment?: string;
  note?: string;
};

/** Sửa nhãn trực tiếp — chỉ field gửi mới cập nhật; nuôi few-shot BE. */
export function useSubmitCorrection(id: string) {
  const invalidate = useInvalidateReviewTargets();
  return useMutation({
    mutationFn: (body: CorrectionBody) =>
      apiFetch<CorrectionResponse>(`/api/corrections/${id}`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

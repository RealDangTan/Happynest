"use client";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { deriveJourney, type Journey } from "@/lib/journey";
import type {
  FeedbackListResponse,
  ImportListResponse,
  InsightsListResponse,
  RunListResponse,
} from "@/lib/types";
import { useActions } from "@/hooks/use-actions";
import { useProduct } from "@/hooks/use-product";
import { useTaxonomy } from "@/hooks/use-taxonomy";

const ACTIVE_IMPORT = new Set(["profile_ready", "mapping_generating", "mapping_review", "importing"]);

/**
 * Trạng thái lộ trình E2E cho product đang chọn (plan 41). Query key dùng
 * chung tiền tố với các màn ("imports", "feedbacks", "insights", "actions",
 * "analysis") nên mọi mutation đang invalidate ở đó cũng làm mới lộ trình —
 * không cần poll dày. Chỉ poll nhanh khi hệ thống đang chạy nền.
 */
export function useJourney(): { journey: Journey | null; ready: boolean } {
  const { productId, products, loading } = useProduct();
  const enabled = productId != null;

  const imports = useQuery({
    queryKey: ["imports", "product", productId],
    queryFn: () =>
      apiFetch<ImportListResponse>(`/api/imports?limit=50&product_id=${productId}`),
    enabled,
    refetchInterval: (q) =>
      q.state.data?.items.some((i) => ACTIVE_IMPORT.has(i.status)) ? 4000 : 30_000,
  });

  const running = useQuery({
    queryKey: ["analysis", "runs", "journey"],
    queryFn: () => apiFetch<RunListResponse>("/api/analysis/runs?limit=10&status=running"),
    enabled,
    // Chỉ lượt phân loại (có import_id) mới cần nhịp nhanh — row của cuộc điều
    // tra AI bỏ dở giữ `running` vĩnh viễn và từng ép poll 4s mãi mãi.
    refetchInterval: (q) =>
      q.state.data?.items.some((r) => r.import_id != null) ? 4000 : 30_000,
  });
  const productImportIds = useMemo(
    () => new Set((imports.data?.items ?? []).map((i) => i.id)),
    [imports.data],
  );
  const runningRun =
    running.data?.items.find(
      (r) => r.status === "running" && r.import_id && productImportIds.has(r.import_id),
    ) ?? null;
  // Run vừa xong → đếm lại pending/analyzed theo nhịp nhanh để lộ trình bước tiếp.
  const countInterval = runningRun ? 5000 : 60_000;
  // File vừa nhập xong → key đổi → đếm lại ngay, không chờ nhịp poll.
  const importedCount =
    imports.data?.items.filter((i) => i.status === "imported").length ?? 0;

  const pending = useQuery({
    queryKey: ["feedbacks", "journey", "pending", productId, importedCount],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=pending&product_id=${productId}`,
      ),
    enabled,
    refetchInterval: countInterval,
    placeholderData: (previous) => previous,
  });
  const analyzed = useQuery({
    queryKey: ["feedbacks", "journey", "completed", productId, importedCount],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=completed&product_id=${productId}`,
      ),
    enabled,
    refetchInterval: countInterval,
    placeholderData: (previous) => previous,
  });

  const uncategorized = useQuery({
    queryKey: ["feedbacks", "journey", "uncategorized", productId, importedCount],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=uncategorized&product_id=${productId}`,
      ),
    enabled,
    refetchInterval: countInterval,
    placeholderData: (previous) => previous,
  });
  const taxonomy = useTaxonomy(productId);

  const insights = useQuery({
    queryKey: ["insights", "journey", productId],
    queryFn: () => apiFetch<InsightsListResponse>(`/api/insights?product_id=${productId}`),
    enabled,
    // Có kết luận đang chờ duyệt → poll nhanh để lộ trình sang bước kế ngay
    // sau khi duyệt (quyết định lưu nền, không invalidate key này).
    refetchInterval: (q) =>
      q.state.data?.items.some((i) => i.status === "pending" || i.status === "investigating")
        ? 5000
        : 30_000,
  });
  const latestApproved = useMemo(
    () =>
      [...(insights.data?.items ?? [])]
        .filter((i) => i.status === "approved" || i.status === "edited")
        .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null,
    [insights.data],
  );
  const actions = useActions(latestApproved?.id ?? null);

  const ready =
    !loading &&
    (!enabled ||
      (imports.isSuccess && pending.isSuccess && analyzed.isSuccess && insights.isSuccess));

  const journey = useMemo(() => {
    if (!ready) return null;
    const actionItems = actions.data?.items;
    return deriveJourney({
      hasProduct: products.length > 0 && enabled,
      imports: imports.data?.items ?? [],
      pendingCount: pending.data?.total ?? 0,
      pendingImportId: pending.data?.items[0]?.import_id ?? null,
      analyzedCount: analyzed.data?.total ?? 0,
      runningAnalysis: runningRun
        ? {
            id: runningRun.id,
            importId: runningRun.import_id,
            processed: runningRun.processed_count,
            total: runningRun.total_count,
          }
        : null,
      insights: insights.data?.items ?? [],
      topicCount: taxonomy.data
        ? taxonomy.data.items.filter((n) => n.status === "active").length
        : null,
      uncategorizedCount: uncategorized.data?.total ?? 0,
      actions:
        latestApproved && actionItems
          ? {
              insightId: latestApproved.id,
              total: actionItems.length,
              accepted: actionItems.filter((a) => a.status === "accepted").length,
              open: actionItems.filter(
                (a) => a.status === "proposed" || a.status === "edited",
              ).length,
            }
          : null,
    });
  }, [
    ready,
    actions.data,
    products.length,
    enabled,
    imports.data,
    pending.data,
    analyzed.data,
    runningRun,
    insights.data,
    latestApproved,
    taxonomy.data,
    uncategorized.data,
  ]);

  return { journey, ready };
}

import type {
  ActivityInvestigation,
  ActivitySummary,
  ImportRecord,
  RunProgress,
} from "./types";

const ATTENTION = new Set(["profile_ready", "mapping_review"]);
const IMPORT_RUNNING = new Set(["mapping_generating", "importing"]);

export function deriveActivitySummary({
  imports,
  runs,
  seenFailures,
  completedRecently,
  investigation = null,
}: {
  imports: ImportRecord[];
  runs: RunProgress[];
  seenFailures: string;
  completedRecently: boolean;
  /** Cuộc điều tra AI đang mở (nếu có). Trước đây bộ đếm chỉ tính import và
   * lượt phân loại nên hiện "0 running" trong lúc AI đang điều tra (HN-016). */
  investigation?: ActivityInvestigation | null;
}): ActivitySummary & { failedSignature: string } {
  const investigating =
    investigation?.status === "running" ||
    investigation?.status === "decision_processing";
  const awaitingReview = investigation?.status === "pending_approval";
  const attention = imports.filter((item) => ATTENTION.has(item.status));
  const runningImports = imports.filter((item) => IMPORT_RUNNING.has(item.status));
  const scopedRuns = runs.filter(
    (run) => run.import_id && (run.mode === "selected" || run.mode === "batch"),
  );
  const runningRuns = scopedRuns.filter((run) => run.status === "running");
  const failedSignature = [
    ...imports.filter((item) => item.status === "failed").map((item) => `i:${item.id}`),
    ...scopedRuns.filter((run) => run.status === "failed").map((run) => `r:${run.id}`),
  ].sort().join("|");
  const runningCount =
    runningImports.length + runningRuns.length + (investigating ? 1 : 0);
  const attentionCount = attention.length + (awaitingReview ? 1 : 0);
  const primaryActivity = attention[0]
    ? { kind: "import" as const, id: attention[0].id }
    : runningImports[0]
      ? { kind: "import" as const, id: runningImports[0].id }
      : runningRuns[0]
        ? { kind: "run" as const, id: runningRuns[0].id }
        : null;
  const state = failedSignature && failedSignature !== seenFailures
    ? "failed"
    : runningCount
      ? "running"
      : attentionCount
        ? "needs_attention"
        : completedRecently
          ? "completed"
          : "idle";
  return {
    state,
    attentionCount,
    runningCount,
    primaryActivity,
    failedSignature,
  };
}

export function withActivityParam(query: string, value: string | null): string {
  const params = new URLSearchParams(query);
  if (value) params.set("activity", value);
  else params.delete("activity");
  return params.toString();
}

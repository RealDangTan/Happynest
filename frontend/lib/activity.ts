import type { ActivitySummary, ImportRecord, RunProgress } from "./types";

const ATTENTION = new Set(["profile_ready", "mapping_review"]);
const IMPORT_RUNNING = new Set(["mapping_generating", "importing"]);

export function deriveActivitySummary({
  imports,
  runs,
  seenFailures,
  completedRecently,
}: {
  imports: ImportRecord[];
  runs: RunProgress[];
  seenFailures: string;
  completedRecently: boolean;
}): ActivitySummary & { failedSignature: string } {
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
  const runningCount = runningImports.length + runningRuns.length;
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
      : attention.length
        ? "needs_attention"
        : completedRecently
          ? "completed"
          : "idle";
  return {
    state,
    attentionCount: attention.length,
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

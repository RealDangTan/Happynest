import { describe, expect, it } from "vitest";
import { deriveActivitySummary, withActivityParam } from "./activity";
import type { ImportRecord, RunProgress } from "./types";

const importRow = (status: ImportRecord["status"], id: string = status): ImportRecord => ({
  id,
  product_id: "p",
  source_type: "csv",
  storage_path: null,
  original_filename: "sample.csv",
  mapping_version: null,
  schema_version: null,
  status,
  row_count: null,
  source_row_count: 3,
  column_profiles: [],
  report: null,
  mapping_started_at: null,
  error: null,
  created_at: "2026-08-30T00:00:00Z",
});

const runRow = (status: RunProgress["status"]): RunProgress => ({
  id: status,
  status,
  processed_count: 0,
  total_count: 10,
  error: null,
  started_at: "2026-08-30T00:00:00Z",
  completed_at: null,
  pipeline_version: "v2",
  llm_model: "m",
  prompt_version: "v2",
  embedding_model: "e",
  import_id: "i",
  mode: "batch",
  chunk_size: 10,
  failed_count: 0,
  cancel_requested_at: null,
});

describe("activity summary", () => {
  it("counts attention and running jobs with running state", () => {
    const result = deriveActivitySummary({
      imports: [importRow("profile_ready"), importRow("mapping_review"), importRow("importing")],
      runs: [runRow("running")],
      seenFailures: "",
      completedRecently: false,
    });
    expect(result.state).toBe("running");
    expect(result.attentionCount).toBe(2);
    expect(result.runningCount).toBe(2);
  });

  it("keeps an unseen failure destructive until opened", () => {
    const result = deriveActivitySummary({
      imports: [importRow("failed", "broken")],
      runs: [],
      seenFailures: "",
      completedRecently: false,
    });
    expect(result.state).toBe("failed");
    expect(result.failedSignature).toBe("i:broken");
  });
});

describe("activity query param", () => {
  it("opens and closes activity without losing existing filters", () => {
    expect(withActivityParam("page=2&severity=high", "import:abc")).toBe("page=2&severity=high&activity=import%3Aabc");
    expect(withActivityParam("page=2&activity=queue&severity=high", null)).toBe("page=2&severity=high");
  });
});

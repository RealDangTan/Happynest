import { describe, expect, it } from "vitest";
import { topTopics, trendByDate, analysisStats, scopeLine } from "./graph";
import type { Feedback } from "./types";

function fb(over: Partial<Feedback>): Feedback {
  return {
    id: "f-1",
    product_id: "p-1",
    import_id: "imp-1",
    source: "survey",
    source_record_id: null,
    occurred_at: "2026-09-01T10:00:00Z",
    imported_at: "2026-09-14T00:00:00Z",
    feedback_text: "<ORG> received a slow answer.",
    pii_detected: false,
    data: {},
    source_meta: {},
    ai_analysis: {
      topics: ["Performance"],
      ai_issue: null,
      sentiment: "negative",
      severity: "medium",
      safety_issue: false,
      confidence: 0.9,
      rationale: null,
      analysis_version: "v1",
    },
    created_at: "2026-09-14T00:00:00Z",
    ...over,
  };
}

describe("topTopics", () => {
  it("counts topics across analyzed feedback, sorted desc", () => {
    const items = [
      fb({ id: "1", ai_analysis: { ...fb({}).ai_analysis!, topics: ["Accuracy", "Speed"] } }),
      fb({ id: "2", ai_analysis: { ...fb({}).ai_analysis!, topics: ["Accuracy"] } }),
      fb({ id: "3", ai_analysis: null }),
    ];
    expect(topTopics(items)).toEqual([
      { topic: "Accuracy", count: 2 },
      { topic: "Speed", count: 1 },
    ]);
  });
});

describe("trendByDate", () => {
  it("groups by occurred_at date ascending", () => {
    const items = [
      fb({ id: "1", occurred_at: "2026-09-02T00:00:00Z" }),
      fb({ id: "2", occurred_at: "2026-09-01T00:00:00Z" }),
      fb({ id: "3", occurred_at: "2026-09-02T05:00:00Z" }),
    ];
    expect(trendByDate(items)).toEqual([
      { date: "2026-09-01", count: 1 },
      { date: "2026-09-02", count: 2 },
    ]);
  });
});

describe("analysisStats", () => {
  it("separates analyzed from pending", () => {
    const items = [
      fb({ id: "1", ai_analysis: fb({}).ai_analysis }),
      fb({ id: "2", ai_analysis: null }),
    ];
    expect(analysisStats(items)).toEqual({ analyzed: 1, pending: 1 });
  });
});

describe("scopeLine", () => {
  it("summarizes imports, period and analysis counts", () => {
    expect(scopeLine(2, "2026-09-01", "2026-09-14", 120, 15)).toBe(
      "2 imports / Sep 1 – Sep 14 / 120 analyzed / 15 pending excluded",
    );
  });
});

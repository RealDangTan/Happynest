import { describe, expect, it } from "vitest";
import { topTopics, topicLabeler, trendByDate, analysisStats, scopeLine } from "./graph";
import type { Feedback, TaxonomyNode } from "./types";

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

describe("topicLabeler", () => {
  const taxonomy = [
    {
      id: "t-1",
      product_id: "p-1",
      parent_id: null,
      name: "AI Quality",
      name_vi: "Chất lượng AI",
      slug: "ai_quality",
      description: null,
      kind: "canonical",
      status: "active",
      evidence_count: 3,
      first_seen: null,
      last_seen: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    {
      id: "t-2",
      product_id: "p-1",
      parent_id: null,
      name: "Payment Failure",
      name_vi: "Lỗi thanh toán",
      slug: "payment.payment_failure",
      description: null,
      kind: "canonical",
      status: "active",
      evidence_count: 1,
      first_seen: null,
      last_seen: null,
      created_at: "2026-09-01T00:00:00Z",
    },
  ] as TaxonomyNode[];

  it("maps slug to the Vietnamese display name", () => {
    const label = topicLabeler(taxonomy);
    expect(label("ai_quality")).toBe("Chất lượng AI");
    expect(label("payment.payment_failure")).toBe("Lỗi thanh toán");
  });

  it("passes through unknown or legacy topics unchanged", () => {
    const label = topicLabeler(taxonomy);
    expect(label("Search")).toBe("Search");
    expect(label("removed.slug")).toBe("removed.slug");
  });

  it("prefers active canonical node when slugs collide", () => {
    const pending = { ...taxonomy[0], id: "t-3", name: "Old", name_vi: "Cũ", status: "pending_review" as const };
    const label = topicLabeler([pending, ...taxonomy]);
    expect(label("ai_quality")).toBe("Chất lượng AI");
  });

  it("falls back to canonical English name when name_vi is null", () => {
    const label = topicLabeler([
      { ...taxonomy[0], name: "AI Quality", name_vi: null },
    ]);
    expect(label("ai_quality")).toBe("AI Quality");
  });
});

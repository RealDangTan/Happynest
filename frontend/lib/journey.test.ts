import { describe, expect, it } from "vitest";
import { deriveJourney, type JourneyInput } from "./journey";

function input(over: Partial<JourneyInput> = {}): JourneyInput {
  return {
    hasProduct: true,
    imports: [],
    pendingCount: 0,
    pendingImportId: null,
    analyzedCount: 0,
    runningAnalysis: null,
    insights: [],
    actions: null,
    topicCount: 5,
    uncategorizedCount: 0,
    ...over,
  };
}

const imported = {
  id: "imp-1",
  status: "imported" as const,
  original_filename: "reviews.csv",
  created_at: "2026-11-01T00:00:00Z",
};

describe("deriveJourney — next action", () => {
  it("asks for a product before anything else", () => {
    const j = deriveJourney(input({ hasProduct: false }));
    expect(j.next.kind).toBe("create-product");
    expect(j.next.href).toBe("/onboarding");
  });

  it("starts with the first import on an empty workspace", () => {
    const j = deriveJourney(input());
    expect(j.next).toMatchObject({ kind: "import-first", step: "import", href: "/importer?new=1" });
    expect(j.steps.import.status).toBe("current");
    expect(j.steps.classify.status).toBe("upcoming");
  });

  it("resumes an import still waiting for its mapping review", () => {
    const j = deriveJourney(
      input({
        imports: [
          imported,
          { id: "imp-2", status: "mapping_review", original_filename: "new.csv", created_at: "2026-11-02T00:00:00Z" },
        ],
      }),
    );
    expect(j.next).toMatchObject({ kind: "finish-mapping", href: "/importer?import=imp-2", label: "new.csv" });
  });

  it("waits (no CTA target) while a file is importing", () => {
    const j = deriveJourney(
      input({ imports: [{ ...imported, status: "importing" }] }),
    );
    expect(j.next.kind).toBe("importing");
    expect(j.next.waiting).toBe(true);
  });

  it("sends a fresh import to classification, scoped to the import holding pending rows", () => {
    const j = deriveJourney(input({ imports: [imported], pendingCount: 12, pendingImportId: "imp-1" }));
    expect(j.next).toMatchObject({
      kind: "classify",
      step: "classify",
      count: 12,
      href: "/vault?import=imp-1&analyze=1",
    });
    expect(j.steps.import.status).toBe("done");
  });

  it("builds the topic set before the first classification", () => {
    const j = deriveJourney(
      input({ imports: [imported], pendingCount: 12, pendingImportId: "imp-1", topicCount: 0 }),
    );
    expect(j.next).toMatchObject({ kind: "build-topics", step: "classify", href: "/taxonomy?generate=1" });
  });

  it("does not block on topics while their count is still unknown", () => {
    const j = deriveJourney(
      input({ imports: [imported], pendingCount: 12, pendingImportId: "imp-1", topicCount: null }),
    );
    expect(j.next.kind).toBe("classify");
  });

  it("re-classifies when everything landed in UNCATEGORIZED and topics now exist", () => {
    const j = deriveJourney(
      input({ imports: [imported], analyzedCount: 9, uncategorizedCount: 9, topicCount: 6 }),
    );
    expect(j.next).toMatchObject({ kind: "reclassify", step: "classify", count: 9, href: "/vault?reclassify=1" });
    expect(j.steps.classify.status).toBe("current");
  });

  it("asks for topics first when everything is UNCATEGORIZED and no topic exists", () => {
    const j = deriveJourney(
      input({ imports: [imported], analyzedCount: 9, uncategorizedCount: 9, topicCount: 0 }),
    );
    expect(j.next.kind).toBe("build-topics");
  });

  it("shows progress while classification runs", () => {
    const j = deriveJourney(
      input({
        imports: [imported],
        pendingCount: 5,
        pendingImportId: "imp-1",
        runningAnalysis: { id: "run-1", importId: "imp-1", processed: 3, total: 8 },
      }),
    );
    expect(j.next).toMatchObject({ kind: "classifying", waiting: true, progress: { done: 3, total: 8 } });
  });

  it("moves to asking AI once feedback is classified", () => {
    const j = deriveJourney(input({ imports: [imported], analyzedCount: 20 }));
    expect(j.next).toMatchObject({ kind: "ask", step: "investigate", href: "/data-graph?ask=1" });
    expect(j.steps.classify.status).toBe("done");
  });

  it("does not nag about leftover pending rows from an older import", () => {
    const j = deriveJourney(
      input({
        imports: [
          { id: "imp-new", status: "imported", original_filename: "b.csv", created_at: "2026-11-02T00:00:00Z" },
          imported,
        ],
        analyzedCount: 30,
        pendingCount: 4,
        pendingImportId: "imp-1",
      }),
    );
    expect(j.next.kind).toBe("ask");
    expect(j.steps.classify.count).toBe(4);
  });

  it("prioritises a finding waiting for review", () => {
    const j = deriveJourney(
      input({
        imports: [imported],
        analyzedCount: 20,
        insights: [
          { id: "ins-1", run_id: "run-a", status: "pending", title: "Login loops", created_at: "2026-11-02T00:00:00Z" },
        ],
      }),
    );
    expect(j.next).toMatchObject({ kind: "review-finding", href: "/data-graph?run=run-a", label: "Login loops" });
    expect(j.steps.investigate.count).toBe(1);
  });

  it("asks to generate actions for the newest approved finding without any", () => {
    const j = deriveJourney(
      input({
        imports: [imported],
        analyzedCount: 20,
        insights: [
          { id: "old", run_id: "r0", status: "approved", title: "Old", created_at: "2026-11-01T00:00:00Z" },
          { id: "new", run_id: "r1", status: "edited", title: "New", created_at: "2026-11-02T00:00:00Z" },
        ],
        actions: { insightId: "new", total: 0, open: 0, accepted: 0 },
      }),
    );
    expect(j.next).toMatchObject({ kind: "generate-actions", step: "act", href: "/matrix?report=new", label: "New" });
    expect(j.steps.investigate.status).toBe("done");
  });

  it("asks for decisions on open actions, then hands off once one is accepted", () => {
    const base = input({
      imports: [imported],
      analyzedCount: 20,
      insights: [{ id: "ins", run_id: "r", status: "approved", title: "T", created_at: "2026-11-02T00:00:00Z" }],
    });
    expect(
      deriveJourney({ ...base, actions: { insightId: "ins", total: 3, open: 3, accepted: 0 } }).next,
    ).toMatchObject({ kind: "decide-actions", count: 3, href: "/matrix?report=ins" });

    const done = deriveJourney({ ...base, actions: { insightId: "ins", total: 3, open: 1, accepted: 2 } });
    expect(done.next).toMatchObject({ kind: "handoff", step: "handoff", href: "/stakeholders?report=ins" });
    expect(done.steps.act.status).toBe("done");
    expect(done.steps.handoff.status).toBe("current");
  });

  it("uses a neutral actions step while action state is still unknown", () => {
    const j = deriveJourney(
      input({
        imports: [imported],
        analyzedCount: 20,
        insights: [{ id: "ins", run_id: "r", status: "approved", title: "T", created_at: "2026-11-02T00:00:00Z" }],
        actions: null,
      }),
    );
    expect(j.next).toMatchObject({ kind: "open-actions", href: "/matrix?report=ins", waiting: false });
  });
});

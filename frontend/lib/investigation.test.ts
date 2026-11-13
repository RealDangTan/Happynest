import { describe, expect, it } from "vitest";
import {
  SLOW_INVESTIGATION_MS,
  formatElapsed,
  isSlowInvestigation,
  readableEvidence,
  restoreSession,
} from "./investigation";

describe("investigation progress clock (HN-016)", () => {
  const start = "2026-11-11T14:43:00Z";
  const at = (ms: number) => new Date(start).getTime() + ms;

  it("formats elapsed time as m:ss and never goes negative", () => {
    expect(formatElapsed(start, at(23_000))).toBe("0:23");
    expect(formatElapsed(start, at(233_000))).toBe("3:53");
    expect(formatElapsed(start, at(-5_000))).toBe("0:00");
  });

  it("marks a run slow only past the threshold", () => {
    expect(isSlowInvestigation(start, at(SLOW_INVESTIGATION_MS - 1))).toBe(false);
    expect(isSlowInvestigation(start, at(SLOW_INVESTIGATION_MS))).toBe(true);
    expect(isSlowInvestigation(null, at(SLOW_INVESTIGATION_MS))).toBe(false);
  });
});

describe("investigation evidence", () => {
  it("turns aggregate payload into readable counts without internal keys", () => {
    const text = readableEvidence('aggregate_feedback: {"group_by":"topic","coverage":0.75,"rows":[{"value":"Login","count":12,"avg_confidence":null}]}');
    expect(text).toContain("Login");
    expect(text).toContain("12");
    expect(text).toContain("75%");
    expect(text).not.toContain("avg_confidence");
    expect(text).not.toContain("aggregate_feedback");
  });
  it("keeps ordinary evidence but masks opaque identifiers", () => {
    expect(readableEvidence("Complaints increased by 12%.")).toBe("Complaints increased by 12%.");
    expect(readableEvidence("Evidence 10cf50d4-926a-4544-956f-2b31375525c4 supports this.")).not.toContain("10cf50d4");
  });
  it("does not present truncated JSON as a conclusion", () => {
    expect(readableEvidence('get_schema: {"dimensions":[')).not.toContain('"dimensions"');
  });
});

describe("product investigation session", () => {
  it("restores run and question for its product only", () => {
    const saved = JSON.stringify({productId:"p1",value:{runId:"run1",question:"Why?"}});
    expect(restoreSession(saved, "p1", null)).toEqual({runId:"run1",question:"Why?"});
    expect(restoreSession(saved, "p2", null)).toBeNull();
    expect(restoreSession("{broken", "p1", null)).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { readableEvidence, restoreSession } from "./investigation";

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

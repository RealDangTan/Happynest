import { describe, expect, it } from "vitest";
import { autoIgnoredDuplicates } from "./import-steps";
import type { MappingItem } from "@/lib/types";

function item(over: Partial<MappingItem>): MappingItem {
  return {
    source_field: "col",
    decision: "MAP",
    target: "feedback_text",
    candidate: null,
    confidence: 0.8,
    reason: "",
    needs_human_review: false,
    ...over,
  };
}

describe("autoIgnoredDuplicates", () => {
  it("keeps the content-like column when AI maps two columns to one target", () => {
    const ignored = autoIgnoredDuplicates([
      item({ source_field: "title" }),
      item({ source_field: "content" }),
      item({ source_field: "reviewed_date", target: "occurred_at" }),
    ]);
    expect([...ignored]).toEqual([["title", "content"]]);
  });

  it("prefers higher confidence over the column name", () => {
    const ignored = autoIgnoredDuplicates([
      item({ source_field: "body", confidence: 0.4 }),
      item({ source_field: "summary", confidence: 0.9 }),
    ]);
    expect(ignored.get("body")).toBe("summary");
  });

  it("leaves distinct targets and non-field decisions alone", () => {
    const ignored = autoIgnoredDuplicates([
      item({ source_field: "content" }),
      item({ source_field: "id", decision: "SOURCE_META", target: null }),
      item({ source_field: "rating", decision: "AMBIGUOUS", target: null }),
    ]);
    expect(ignored.size).toBe(0);
  });
});

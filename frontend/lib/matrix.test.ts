import { describe, expect, it } from "vitest";
import { quadrantOf, effectiveScores, QUADRANT_LABEL } from "./matrix";
import type { ActionItem } from "./types";

function action(over: Partial<ActionItem>): ActionItem {
  return {
    id: "a-1",
    insight_id: "i-1",
    function: "ENGINEERING",
    recommendation: "Improve citation fallback",
    rationale: "",
    impact: 8,
    effort: 3,
    urgency: 9,
    confidence: 0.84,
    priority_score: 0,
    human_impact: null,
    human_effort: null,
    human_urgency: null,
    override_reason: null,
    status: "proposed",
    created_at: "2026-09-15T00:00:00Z",
    ...over,
  };
}

describe("quadrantOf", () => {
  it("mirrors the backend split (impact >= 5 high, effort <= 5 low)", () => {
    expect(quadrantOf(8, 3)).toBe("quick_wins");
    expect(quadrantOf(8, 7)).toBe("strategic_investments");
    expect(quadrantOf(3, 3)).toBe("low_priority");
    expect(quadrantOf(3, 7)).toBe("reconsider");
  });

  it("treats the 5/5 boundary like the backend", () => {
    expect(quadrantOf(5, 5)).toBe("quick_wins");
    expect(quadrantOf(4, 5)).toBe("low_priority");
  });
});

describe("effectiveScores", () => {
  it("uses agent values until a human override exists", () => {
    const a = action({});
    expect(effectiveScores(a)).toEqual({ impact: 8, effort: 3, urgency: 9 });
    const overridden = action({ human_impact: 6, human_effort: 4 });
    expect(effectiveScores(overridden)).toEqual({ impact: 6, effort: 4, urgency: 9 });
  });
});

describe("QUADRANT_LABEL", () => {
  it("names all four quadrants", () => {
    expect(Object.keys(QUADRANT_LABEL).sort()).toEqual(
      ["low_priority", "quick_wins", "reconsider", "strategic_investments"].sort(),
    );
    expect(QUADRANT_LABEL.quick_wins).toBe("Quick wins");
  });
});

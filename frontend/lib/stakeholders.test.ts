import { describe, expect, it } from "vitest";
import { countByStatus, filterStakeholderActions } from "./stakeholders";
import type { ActionItem } from "./types";

function action(over: Partial<ActionItem>): ActionItem {
  return {
    id: "a-1",
    insight_id: "i-1",
    function: "ENGINEERING",
    recommendation: "Ship the launch fix",
    rationale: "",
    impact: 9,
    effort: 7,
    urgency: 9,
    confidence: 0.8,
    priority_score: 8.6,
    human_impact: null,
    human_effort: null,
    human_urgency: null,
    override_reason: null,
    status: "proposed",
    created_at: "2026-11-11T00:00:00Z",
    ...over,
  };
}

// Đúng dữ liệu QA 2026-11-11: Engineering đã nhận + Support còn đề xuất.
const items = [
  action({ id: "eng", function: "ENGINEERING", status: "accepted" }),
  action({ id: "sup", function: "SUPPORT", status: "proposed" }),
];

describe("filterStakeholderActions", () => {
  it("shows every status under All (HN-010)", () => {
    const result = filterStakeholderActions(items, {
      department: "all",
      status: "all",
      selectedId: null,
    });
    expect(result.map((a) => a.id)).toEqual(["eng", "sup"]);
  });

  it("keeps All consistent with the department counters", () => {
    const result = filterStakeholderActions(items, {
      department: "support",
      status: "all",
      selectedId: null,
    });
    expect(result.map((a) => a.id)).toEqual(["sup"]);
  });

  it("filters by a single status", () => {
    const only = (status: "accepted" | "proposed" | "rejected") =>
      filterStakeholderActions(items, {
        department: "all",
        status,
        selectedId: null,
      }).map((a) => a.id);
    expect(only("accepted")).toEqual(["eng"]);
    expect(only("proposed")).toEqual(["sup"]);
    expect(only("rejected")).toEqual([]);
  });

  it("keeps the selected undecided action visible under Accepted", () => {
    const result = filterStakeholderActions(items, {
      department: "all",
      status: "accepted",
      selectedId: "sup",
    });
    expect(result.map((a) => a.id)).toEqual(["eng", "sup"]);
  });
});

describe("countByStatus", () => {
  it("counts actions per status", () => {
    expect(countByStatus(items)).toEqual({ accepted: 1, proposed: 1 });
  });
});

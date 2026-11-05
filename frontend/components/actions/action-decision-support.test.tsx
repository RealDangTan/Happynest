import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ActionDecisionSupport } from "./action-decision-support";

const brief = {
  library_version: "act-practices-v1",
  basis_recommendation: "Test answer correction",
  basis_rationale: "Reviewed finding",
  kind: "investigate" as const,
  evidence: [{ evidence_id: "e-1", statement: "Users cannot correct answers", source_tool: "aggregate_feedback" }],
  perspectives: [
    { lens: "ux" as const, assessment: "Reduce correction friction" },
    { lens: "product" as const, assessment: "Validate the need" },
  ],
  references: [{
    card_id: "hax-correction", lens: "ux" as const, source_title: "Microsoft HAX",
    url: "https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/",
    section: "G9 — Support efficient correction", principle: "Support correction",
    applies_when: "AI mistakes", limitations: "Does not fix model accuracy",
    reviewed_on: "2026-10-09", application: "Test an editable answer",
  }],
  source_gap: null,
  alternative: { recommendation: "Replace the model", tradeoff: "Higher cost" },
  tradeoff: "Small trial takes time", assumptions: ["Correction is a bottleneck"],
  success_criteria: "Measure task completion", estimate_basis: "Engineering must validate effort",
};

function render(support: typeof brief | null = brief, recommendation = brief.basis_recommendation, rationale = brief.basis_rationale) {
  return renderToStaticMarkup(<ActionDecisionSupport action={{ recommendation, rationale, decision_support: support }} />);
}

describe("action decision support", () => {
  it("renders tool evidence as readable text, never raw JSON", () => {
    const html = render({
      ...brief,
      evidence: [{
        evidence_id: "e-2",
        statement: 'inspect_cluster: {"cluster_id": "03bb95ec-0bcb-4fdd-9418-495e1c793389", "name": "Lỗi đăng nhập", "feedback_count": 9, "is_emerging": f',
        source_tool: "inspect_cluster",
      }],
    });
    expect(html).toContain("Lỗi đăng nhập");
    expect(html).toContain("Số phản hồi");
    expect(html).not.toContain("cluster_id");
    expect(html).not.toContain("03bb95ec");
  });

  it("shows internal evidence separately from external guidance and application", () => {
    const html = render();
    expect(html).toContain("Users cannot correct answers");
    expect(html).toContain('href="https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/"');
    expect(html).toContain("Test an editable answer");
    expect(html).toContain("Higher cost");
    expect(html).toContain("Measure task completion");
  });

  it("identifies the original analysis after recommendation or rationale edits", () => {
    expect(render(brief, "A different action")).toContain("đề xuất gốc của AI");
    expect(render(brief, undefined, "A different rationale")).toContain("đề xuất gốc của AI");
    expect(render()).not.toContain("đề xuất gốc của AI");
  });

  it("does not invent analysis for legacy or manual actions", () => {
    const html = render(null);
    expect(html).toContain("Chưa có phân tích");
    expect(html).not.toContain("Microsoft HAX");
  });

  it("does not render unsafe source links", () => {
    const unsafe = { ...brief, references: [{ ...brief.references[0], url: "javascript:alert(1)" }] };
    expect(render(unsafe)).not.toContain('href="javascript:');
  });
});

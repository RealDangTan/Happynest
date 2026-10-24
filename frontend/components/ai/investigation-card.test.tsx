import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FindingReview } from "./investigation-card";
import type { PendingApproval } from "@/lib/types";

const pending: PendingApproval = {
  insight_id: "opaque-id", insight: {title:"Login issue",finding:"12 reports",finding_confidence:0.8,affected_context:{},impact:[],limitations:[]},
  evidence: [], options: ["approve","edit","investigate_more","reject"],
};

describe("inline finding review", () => {
  it("keeps all four review choices in the investigation instead of navigating to reports", () => {
    const html = renderToStaticMarkup(<FindingReview pending={pending} busy={false} onSubmit={() => {}} />);
    expect(html).toContain("Duyệt kết luận");
    expect(html).toContain("Chỉnh sửa");
    expect(html).toContain("Điều tra thêm");
    expect(html).toContain("Từ chối");
    expect(html).not.toContain("href=");
    expect(html).not.toContain("opaque-id");
  });
  it("disables every review choice while a decision is being saved", () => {
    const html = renderToStaticMarkup(<FindingReview pending={pending} busy onSubmit={() => {}} />);
    expect((html.match(/disabled=""/g) ?? []).length).toBe(4);
    expect(html).toContain('role="status"');
  });
});

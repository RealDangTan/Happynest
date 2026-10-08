import { describe, expect, it } from "vitest";

import {
  displaySlug,
  groupProposalTree,
  groupTaxonomyTree,
  selectedProposalPayload,
} from "./taxonomy";
import type { ProposedTopic, TaxonomyNode } from "./types";

const node = (overrides: Partial<TaxonomyNode>): TaxonomyNode => ({
  id: "id",
  product_id: "p",
  parent_id: null,
  name: "N",
  slug: "n",
  description: null,
  kind: "canonical",
  status: "active",
  evidence_count: 0,
  first_seen: null,
  last_seen: null,
  created_at: "2026-01-01",
  ...overrides,
});

describe("groupProposalTree", () => {
  it("gom con vào đúng cha theo NAME và giữ thứ tự gốc", () => {
    const topics: ProposedTopic[] = [
      { name: "Payment", parent: null },
      { name: "Payment failure", parent: "Payment" },
      { name: "Refund", parent: "Payment" },
      { name: "Search", parent: null },
    ];
    const tree = groupProposalTree(topics);
    expect(tree).toHaveLength(2);
    expect(tree[0].root.name).toBe("Payment");
    expect(tree[0].children.map((c) => c.name)).toEqual([
      "Payment failure",
      "Refund",
    ]);
    expect(tree[1].root.name).toBe("Search");
    expect(tree[1].children).toHaveLength(0);
  });

  it("parent lạ → node thăng cấp root thay vì mất tích", () => {
    const topics: ProposedTopic[] = [
      { name: "Orphan", parent: "Ghost" },
      { name: "Root", parent: null },
    ];
    const tree = groupProposalTree(topics);
    expect(tree.map((r) => r.root.name)).toEqual(["Orphan", "Root"]);
  });
});

describe("groupTaxonomyTree", () => {
  it("dựng cây theo parent_id, bỏ con mồ côi lên root", () => {
    const root = node({ id: "r", name: "Payment", slug: "payment" });
    const child = node({
      id: "c",
      name: "Payment failure",
      slug: "payment.payment_failure",
      parent_id: "r",
    });
    const orphan = node({ id: "x", name: "X", parent_id: "missing" });
    const tree = groupTaxonomyTree([root, child, orphan]);
    expect(tree).toHaveLength(2);
    expect(tree[0].children).toHaveLength(1);
    expect(tree[1].node.id).toBe("x");
  });
});

describe("selectedProposalPayload", () => {
  it("chỉ giữ node được chọn; parent bị bỏ → thăng cấp root", () => {
    const topics: ProposedTopic[] = [
      { name: "Payment", parent: null, selected: false },
      { name: "Payment failure", parent: "Payment" },
      { name: "Search", parent: null },
      { name: "Bỏ", parent: "Search", selected: false },
    ];
    expect(selectedProposalPayload(topics)).toEqual([
      { name: "Payment failure", parent: null, description: null },
      { name: "Search", parent: null, description: null },
    ]);
  });

  it("mặc định selected khi thiếu field", () => {
    expect(selectedProposalPayload([{ name: "A", parent: null }])).toEqual([
      { name: "A", parent: null, description: null },
    ]);
  });
});

describe("displaySlug", () => {
  it("giữ slug, null → gạch", () => {
    expect(displaySlug("payment.payment_failure")).toBe(
      "payment.payment_failure",
    );
    expect(displaySlug(null)).toBe("—");
  });
});

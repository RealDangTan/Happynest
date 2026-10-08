import type { ProposedTopic, TaxonomyNode } from "./types";

/** Proposal phẳng (parent = NAME) → cây hiển thị; parent trốn tránh (không có
 * trong list) được thăng cấp root thay vì mất node. Thứ tự: giữ nguyên thứ tự
 * GPT trả — human đọc theo "mức độ tin" của model. */
export function groupProposalTree(topics: ProposedTopic[]): {
  root: ProposedTopic;
  children: ProposedTopic[];
}[] {
  const names = new Set(topics.map((t) => t.name));
  const roots: { root: ProposedTopic; children: ProposedTopic[] }[] = [];
  const placed = new Set<ProposedTopic>();
  for (const topic of topics) {
    if (!topic.parent || !names.has(topic.parent)) {
      roots.push({ root: topic, children: [] });
      placed.add(topic);
    }
  }
  for (const topic of topics) {
    if (placed.has(topic)) continue;
    const parent = roots.find((r) => r.root.name === topic.parent);
    if (parent) parent.children.push(topic);
    else roots.push({ root: topic, children: [] }); // parent lạ → thăng cấp root
  }
  return roots;
}

/** Node DB active (canonical + emerging active) → cây hiển thị theo parent_id. */
export function groupTaxonomyTree(items: TaxonomyNode[]): {
  node: TaxonomyNode;
  children: TaxonomyNode[];
}[] {
  const byId = new Map(items.map((n) => [n.id, n]));
  const roots: { node: TaxonomyNode; children: TaxonomyNode[] }[] = [];
  for (const node of items) {
    if (!node.parent_id || !byId.has(node.parent_id)) {
      roots.push({ node, children: [] });
    }
  }
  for (const node of items) {
    if (!node.parent_id) continue;
    const parent = roots.find((r) => r.node.id === node.parent_id);
    if (parent) parent.children.push(node);
  }
  return roots;
}

/** Proposal sau review → payload apply: chỉ node được chọn, giữ parent CHỈ khi
 * parent cũng được chọn (parent bị bỏ → node thăng cấp root, không orphan). */
export function selectedProposalPayload(
  topics: ProposedTopic[],
): { name: string; parent: string | null; description: string | null }[] {
  const selected = new Set(
    topics.filter((t) => t.selected !== false).map((t) => t.name),
  );
  return topics
    .filter((t) => t.selected !== false)
    .map((t) => ({
      name: t.name.trim(),
      parent: t.parent && selected.has(t.parent) ? t.parent : null,
      description: t.description ?? null,
    }));
}

/** slug hiển thị đẹp cho chip mono ("payment.payment_failure" → giữ nguyên;
 * null → "—"). */
export function displaySlug(slug: string | null): string {
  return slug ?? "—";
}

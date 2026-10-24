import type { Feedback, TaxonomyNode } from "./types";

/**
 * Nhãn hiển thị tiếng Việt cho topic: `ai_analysis.topics` lưu slug (id bất
 * biến, plan 31) — map sang `name_vi ?? name` (2026-10-23: `name` là canonical
 * tiếng Anh cho classifier, `name_vi` là nhãn hiển thị tiếng Việt). Topic lạ
 * (legacy lưu tên hoặc node đã xoá) hiển thị nguyên giá trị gốc. Node
 * active/canonical thắng khi nhiều node trùng slug.
 */
export function topicLabeler(
  taxonomy: TaxonomyNode[],
): (topic: string) => string {
  const labels = new Map<string, string>();
  const ranks = new Map<string, number>();
  for (const node of taxonomy) {
    if (!node.slug) continue;
    const rank =
      (node.status === "active" ? 2 : 0) + (node.kind === "canonical" ? 1 : 0);
    const prev = ranks.get(node.slug);
    if (prev === undefined || rank >= prev) {
      ranks.set(node.slug, rank);
      labels.set(node.slug, node.name_vi ?? node.name);
    }
  }
  return (topic: string) => labels.get(topic) ?? topic;
}

/** Topic frequency across analyzed feedback in the current scope. */
export function topTopics(items: Feedback[], limit = 12): { topic: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    for (const topic of item.ai_analysis?.topics ?? []) {
      counts.set(topic, (counts.get(topic) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([topic, count]) => ({ topic, count }))
    .sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic))
    .slice(0, limit);
}

/** Feedback volume by occurred_at date, ascending. */
export function trendByDate(items: Feedback[]): { date: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const date = item.occurred_at.slice(0, 10);
    counts.set(date, (counts.get(date) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function analysisStats(items: Feedback[]): { analyzed: number; pending: number } {
  let analyzed = 0;
  let pending = 0;
  for (const item of items) {
    if (item.ai_analysis) analyzed += 1;
    else pending += 1;
  }
  return { analyzed, pending };
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function shortDate(iso: string): string {
  if (!iso || iso.length < 10) return "—";
  const [, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[(m ?? 1) - 1]} ${d}`;
}

export function scopeLine(
  imports: number,
  from: string,
  to: string,
  analyzed: number,
  pending: number,
): string {
  return `${imports} ${imports === 1 ? "import" : "imports"} / ${shortDate(from)} – ${shortDate(
    to,
  )} / ${analyzed} analyzed / ${pending} pending excluded`;
}

import type { Feedback } from "./types";

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

import type { Sentiment, Severity } from "./types";

export const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Thấp",
  medium: "Trung bình",
  high: "Cao",
  critical: "Nghiêm trọng",
};

export const SENTIMENT_LABEL: Record<Sentiment, string> = {
  positive: "Tích cực",
  negative: "Tiêu cực",
  neutral: "Trung lập",
  mixed: "Trộn",
};

/** Map gợi ý 0–1 → nhãn; ngưỡng thuần UI (spec UF-05). */
export function priorityLabel(p: number): string {
  if (p >= 0.66) return "cao";
  if (p >= 0.33) return "trung bình";
  return "thấp";
}

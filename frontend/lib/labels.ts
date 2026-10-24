import type { AppLang } from "@/lib/i18n";
import type { Sentiment, Severity } from "./types";

/** Nhãn theo ngôn ngữ hiển thị — index hai lớp `SEVERITY_LABEL[lang][severity]`
 * để mọi trang dữ liệu dùng chung một nguồn chữ VI/EN. */
export const SEVERITY_LABEL: Record<AppLang, Record<Severity, string>> = {
  vi: {
    low: "Thấp",
    medium: "Trung bình",
    high: "Cao",
    critical: "Nghiêm trọng",
  },
  en: {
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
  },
};

export const SENTIMENT_LABEL: Record<AppLang, Record<Sentiment, string>> = {
  vi: {
    positive: "Tích cực",
    negative: "Tiêu cực",
    neutral: "Trung lập",
    mixed: "Trộn",
  },
  en: {
    positive: "Positive",
    negative: "Negative",
    neutral: "Neutral",
    mixed: "Mixed",
  },
};

/** Map gợi ý 0–1 → nhãn; ngưỡng thuần UI (spec UF-05). */
export function priorityLabel(p: number, lang: AppLang): string {
  if (p >= 0.66) return lang === "vi" ? "cao" : "high";
  if (p >= 0.33) return lang === "vi" ? "trung bình" : "medium";
  return lang === "vi" ? "thấp" : "low";
}

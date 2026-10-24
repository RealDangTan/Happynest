"use client";
import { ChevronDown, ChevronUp, ChevronsDown, ChevronsUp, ChevronsUpDown, CircleHelp, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAppLang } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const SENTIMENTS = {
  very_positive: {icon: ChevronsUp, vi:"Rất tích cực", en:"Very positive", color:"text-sentiment-positive bg-lichen/20"},
  positive: {icon: ChevronUp, vi:"Tích cực", en:"Positive", color:"text-sentiment-positive bg-lichen/10"},
  neutral: {icon: Minus, vi:"Trung lập", en:"Neutral", color:"text-muted-foreground bg-muted"},
  mixed: {icon: ChevronsUpDown, vi:"Trái chiều", en:"Mixed", color:"text-sentiment-mixed bg-warning/10"},
  negative: {icon: ChevronDown, vi:"Tiêu cực", en:"Negative", color:"text-destructive bg-destructive/10"},
  very_negative: {icon: ChevronsDown, vi:"Rất tiêu cực", en:"Very negative", color:"text-destructive bg-destructive/20"},
};

/** Icon + semantic color; text remains available to hover and assistive tools. */
export function SentimentIndicator({value}: {value?: string | null}) {
  const lang = useAppLang();
  if (!value) return <span className="text-muted-foreground" aria-label={lang === "vi" ? "Chưa phân loại" : "Not classified"}>—</span>;
  const normalized = value.toLowerCase().trim().replace(/[ -]+/g,"_");
  const key = normalized === "very_pos" ? "very_positive" : normalized === "very_neg" ? "very_negative" : normalized;
  const sentiment = SENTIMENTS[key as keyof typeof SENTIMENTS];
  const Icon = sentiment?.icon ?? CircleHelp;
  const label = sentiment ? sentiment[lang] : lang === "vi" ? "Chưa xác định cảm xúc" : "Unknown sentiment";
  return <Badge variant="outline" className={cn("size-8 justify-center p-0", sentiment?.color ?? "text-muted-foreground")} title={label} aria-label={label}>
    <Icon className="size-4" aria-hidden="true" />
    <span className="sr-only">{label}</span>
  </Badge>;
}

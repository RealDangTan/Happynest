import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

/** Độ tin cậy AI ước lượng: thanh + phần trăm + mức chữ, đọc được cả khi không nhìn màu. */
export function ConfidenceMeter({
  value,
  label = "Độ tin cậy",
  className,
}: {
  /** 0–1 */
  value: number
  label?: string
  className?: string
}) {
  const pct = Math.round(value * 100)
  const level = pct >= 75 ? "Cao" : pct >= 50 ? "Trung bình" : "Thấp"
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <Progress value={pct} aria-label={`${label} ${pct}%`} className="h-1.5 max-w-32 flex-1" />
      <span className="font-mono text-xs">
        {pct}% · {level}
      </span>
    </div>
  )
}

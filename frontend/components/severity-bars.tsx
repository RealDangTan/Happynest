import { SEVERITY_LABEL } from "@/lib/labels"
import type { Severity } from "@/lib/types"

const ORDER: Severity[] = ["low", "medium", "high", "critical"]

/** Màu theo thứ bậc nghiêm trọng — đậm dần trên thang chart token của app;
 * critical vượt ra destructive vì là mức cần hành động ngay. */
const BAR_COLOR: Record<Severity, string> = {
  low: "bg-chart-1",
  medium: "bg-chart-2",
  high: "bg-chart-4",
  critical: "bg-destructive",
}

/** Bar chart thuần div (không thư viện) — 4 cột low→critical.
 * Count 0 vẫn vẽ cột tối thiểu + số "0" (spec: 0 renders bình thường). */
export function SeverityBars({
  bySeverity,
}: {
  bySeverity: Partial<Record<Severity, number>>
}) {
  const values = ORDER.map((s) => bySeverity[s] ?? 0)
  const max = Math.max(...values, 0)

  return (
    <div
      role="img"
      aria-label={`Phân bố mức độ: ${ORDER.map(
        (s, i) => `${SEVERITY_LABEL[s]} ${values[i]}`
      ).join(", ")}`}
      className="flex items-end justify-around gap-4"
    >
      {ORDER.map((s, i) => (
        <div
          key={s}
          className="flex min-w-14 flex-1 flex-col items-center gap-1"
        >
          <span className="text-sm font-medium tabular-nums">{values[i]}</span>
          {/* khung cố định h-32 để hai chart cạnh nhau cùng chiều cao */}
          <div className="flex h-32 w-full max-w-16 items-end">
            <div
              className={`w-full rounded-t-sm ${BAR_COLOR[s]}`}
              style={{
                height: `${max === 0 ? 0 : Math.max((values[i] / max) * 100, 2)}%`,
              }}
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {SEVERITY_LABEL[s]}
          </span>
        </div>
      ))}
    </div>
  )
}

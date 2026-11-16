"use client"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { SummaryDays } from "@/hooks/use-reports"

export const DAY_OPTIONS: SummaryDays[] = [7, 30, 90]

/** Đọc `?days=` dùng chung cho Tổng quan và Báo cáo tổng hợp (mặc định 30). */
export function useDaysParam(): SummaryDays {
  const sp = useSearchParams()
  const raw = Number(sp.get("days"))
  return DAY_OPTIONS.includes(raw as SummaryDays) ? (raw as SummaryDays) : 30
}

/**
 * Bộ lọc thời gian dùng chung (mẫu Productboard Trends): cùng một điều khiển,
 * cùng tham số URL trên mọi màn số liệu, nên chuyển màn không mất cửa sổ đang xem.
 */
export function TimeRangeToggle() {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const days = useDaysParam()
  return (
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      spacing={0}
      value={String(days)}
      onValueChange={(v) => {
        if (!v) return
        const next = new URLSearchParams(sp.toString())
        next.set("days", v)
        router.replace(`${pathname}?${next.toString()}`, { scroll: false })
      }}
      aria-label="Cửa sổ thời gian"
    >
      {DAY_OPTIONS.map((d) => (
        <ToggleGroupItem key={d} value={String(d)} aria-label={`${d} ngày gần nhất`}>
          {d} ngày
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}

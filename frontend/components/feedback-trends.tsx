"use client"

import { useMemo, useState } from "react"
import { ArrowRight, ChartNoAxesColumn } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useAppLang, useT } from "@/lib/i18n"
import type { Feedback } from "@/lib/types"
import { cn } from "@/lib/utils"

const DAY = 86_400_000
type Period = "day" | "week"
type Bucket = { start: number; end: number; total: number; severe: number }
export type TrendRange = { start: number; end: number; label: string }

export function feedbackDay(item: Feedback) {
  const date = item.occurred_at?.slice(0, 10)
  return date ? Date.parse(date + "T00:00:00Z") : NaN
}

function trendBuckets(items: Feedback[], period: Period): Bucket[] {
  const width = period === "week" ? 7 * DAY : DAY
  const totals = new Map<number, Bucket>()
  let first = Infinity
  let last = -Infinity

  for (const item of items) {
    const day = feedbackDay(item)
    if (!Number.isFinite(day)) continue
    const weekday = new Date(day).getUTCDay()
    const start = period === "week" ? day - ((weekday + 6) % 7) * DAY : day
    const bucket = totals.get(start) ?? { start, end: start + width, total: 0, severe: 0 }
    bucket.total += 1
    if (item.ai_analysis?.severity === "high" || item.ai_analysis?.severity === "critical") {
      bucket.severe += 1
    }
    totals.set(start, bucket)
    first = Math.min(first, start)
    last = Math.max(last, start)
  }

  if (!totals.size) return []
  const maxBuckets = period === "week" ? 12 : 30
  const start = Math.max(first, last - (maxBuckets - 1) * width)
  return Array.from({ length: (last - start) / width + 1 }, (_, index) => {
    const from = start + index * width
    return totals.get(from) ?? { start: from, end: from + width, total: 0, severe: 0 }
  })
}

export function FeedbackTrends({
  items,
  partial,
  onViewFeedback,
}: {
  items: Feedback[]
  partial: boolean
  onViewFeedback: (range: TrendRange) => void
}) {
  const t = useT().graph.trends
  const locale = useAppLang() === "vi" ? "vi-VN" : "en-US"
  const [period, setPeriod] = useState<Period>("day")
  const [selectedStart, setSelectedStart] = useState<number | null>(null)
  const buckets = useMemo(() => trendBuckets(items, period), [items, period])
  const dates = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", timeZone: "UTC" })
  const fullDates = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
  const numbers = new Intl.NumberFormat(locale)
  const formatRange = ({ start, end }: Bucket) => end - start === DAY
    ? fullDates.format(start)
    : fullDates.formatRange(new Date(start), new Date(end - DAY))

  if (!buckets.length) {
    return (
      <Card>
        <CardContent>
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon"><ChartNoAxesColumn /></EmptyMedia>
              <EmptyTitle>{t.emptyTitle}</EmptyTitle>
              <EmptyDescription>{t.emptyDescription}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </CardContent>
      </Card>
    )
  }

  const selected = buckets.find((bucket) => bucket.start === selectedStart)
  const max = Math.max(...buckets.map((bucket) => bucket.total), 1)
  const tickStep = Math.max(1, Math.ceil(max / 4))
  const ceiling = Math.ceil(max / tickStep) * tickStep
  const ticks = Array.from({ length: ceiling / tickStep + 1 }, (_, index) => index * tickStep)
  const sum = buckets.reduce((total, bucket) => total + bucket.total, 0)
  const severe = buckets.reduce((total, bucket) => total + bucket.severe, 0)
  const dateRange = fullDates.formatRange(
    new Date(buckets[0].start),
    new Date(buckets[buckets.length - 1].end - DAY),
  )
  const labelInterval = Math.max(1, Math.ceil(buckets.length / 7))

  return (
    <Card>
      <CardHeader className="gap-2">
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{dateRange} · {t.description}</CardDescription>
      </CardHeader>
      <CardContent className="gap-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <div className="flex items-center gap-2 text-sm">
              <span className="size-2.5 rounded-sm bg-sky" aria-hidden />
              <span>{t.other} <strong className="ml-1 tabular-nums">{numbers.format(sum - severe)}</strong></span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="size-2.5 rounded-sm bg-coral" aria-hidden />
              <span>{t.severe} <strong className="ml-1 tabular-nums">{numbers.format(severe)}</strong></span>
            </div>
          </div>
          <ToggleGroup
            type="single"
            value={period}
            size="sm"
            variant="outline"
            aria-label={t.granularity}
            onValueChange={(value) => {
              if (value !== "day" && value !== "week") return
              setPeriod(value)
              setSelectedStart(null)
            }}
          >
            <ToggleGroupItem value="day">{t.day}</ToggleGroupItem>
            <ToggleGroupItem value="week">{t.week}</ToggleGroupItem>
          </ToggleGroup>
        </div>
        <div className="min-w-0 overflow-x-auto rounded-lg border bg-background/50 px-3 pt-6 pb-2">
          <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-2" style={{ minWidth: buckets.length * 22 + 30 }}>
            <div className="relative h-40 w-7 font-mono text-[10px] tabular-nums text-muted-foreground" aria-hidden>
              {ticks.map((tick) => (
                <span key={tick} className="absolute right-0 translate-y-1/2" style={{ bottom: (tick / ceiling * 100) + "%" }}>
                  {numbers.format(tick)}
                </span>
              ))}
            </div>
            <div className="relative">
              <div className="pointer-events-none absolute inset-x-0 top-0 h-40" aria-hidden>
                {ticks.map((tick) => (
                  <div key={tick} className="absolute inset-x-0 border-t border-border" style={{ bottom: (tick / ceiling * 100) + "%" }} />
                ))}
              </div>
              <div className="relative grid gap-1" role="group" aria-label={t.title} style={{ gridTemplateColumns: "repeat(" + buckets.length + ", minmax(0, 1fr))" }}>
                {buckets.map((bucket, index) => {
                  const label = formatRange(bucket)
                  const active = selectedStart === bucket.start
                  return (
                    <div key={bucket.start} className="flex min-w-0 flex-col items-center gap-2">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            aria-label={label + " · " + t.count(bucket.total) + " · " + t.severe + ": " + bucket.severe}
                            aria-pressed={active}
                            onClick={() => setSelectedStart(active ? null : bucket.start)}
                            className={cn(
                              "flex h-40 w-full items-end justify-center rounded-sm outline-none hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring",
                              active && "bg-accent ring-1 ring-inset ring-ring",
                            )}
                          >
                            <span aria-hidden className={cn("flex w-3/4 max-w-12 flex-col overflow-hidden rounded-t-sm", !bucket.total && "bg-border")} style={{ height: bucket.total ? (bucket.total / ceiling * 100) + "%" : 2 }}>
                              <span className="bg-coral" style={{ flexGrow: bucket.severe }} />
                              <span className="bg-sky" style={{ flexGrow: bucket.total - bucket.severe }} />
                            </span>
                          </button>
                        </TooltipTrigger>
                        <TooltipContent sideOffset={6} className="flex-col items-start gap-1">
                          <strong>{label}</strong>
                          <span>{t.count(bucket.total)} · {t.severe}: {numbers.format(bucket.severe)}</span>
                        </TooltipContent>
                      </Tooltip>
                      <span aria-hidden className="h-5 whitespace-nowrap text-[10px] text-muted-foreground">
                        {index % labelInterval === 0 ? dates.format(bucket.start) : ""}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
        {selected ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-accent/40 px-3 py-2">
            <p className="text-sm" aria-live="polite">
              <strong>{formatRange(selected)}</strong> · {t.count(selected.total)} · {t.severe}: {numbers.format(selected.severe)}
            </p>
            {selected.total > 0 ? (
              <Button size="sm" variant="outline" onClick={() => onViewFeedback({ ...selected, label: formatRange(selected) })}>
                {t.viewFeedback}<ArrowRight data-icon="inline-end" />
              </Button>
            ) : null}
          </div>
        ) : <p className="text-xs text-muted-foreground">{t.pick}</p>}
        {partial && <p className="text-xs text-muted-foreground">{t.partial}</p>}
      </CardContent>
    </Card>
  )
}

"use client"
import { Suspense } from "react"
import Link from "next/link"
import { ReportTiles } from "@/components/report-tiles"
import { SeverityBars } from "@/components/severity-bars"
import { TimeRangeToggle, useDaysParam } from "@/components/time-range-toggle"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useReportSummary } from "@/hooks/use-reports"
import { PageHeader } from "@/components/page-header"
import type { EmergingClusterItem } from "@/lib/types"
import { formatDate } from "@/lib/format"
import { SENTIMENT_LABEL } from "@/lib/labels"
import { useAppLang, useT } from "@/lib/i18n"
import type { Sentiment } from "@/lib/types"

/** Cảm xúc render THEO KEY THỰC TRẢ VỀ của server (4 key gồm mixed) —
 * không hardcode danh sách ô. Một hue duy nhất: phân bố, không phải thứ bậc. */
function SentimentBars({
  bySentiment,
}: {
  bySentiment: Record<string, number>
}) {
  const lang = useAppLang()
  const t = useT()
  const entries = Object.entries(bySentiment)
  const max = Math.max(...entries.map(([, v]) => v), 0)

  return (
    <div
      role="img"
      aria-label={`${t.charts.sentimentDistribution}: ${entries
        .map(([k, v]) => `${SENTIMENT_LABEL[lang][k as Sentiment] ?? k} ${v}`)
        .join(", ")}`}
      className="flex items-end justify-around gap-4"
    >
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="flex min-w-14 flex-1 flex-col items-center gap-1"
        >
          <span className="text-sm font-medium tabular-nums">{value}</span>
          <div className="flex h-32 w-full max-w-16 items-end">
            <div
              className="w-full rounded-t-sm bg-chart-3"
              style={{
                height: `${max === 0 ? 0 : Math.max((value / max) * 100, 2)}%`,
              }}
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {SENTIMENT_LABEL[lang][key as Sentiment] ?? key}
          </span>
        </div>
      ))}
    </div>
  )
}

/** Top chủ đề dạng thanh ngang + tỉ trọng: đọc được thứ hạng lẫn độ chênh. */
function CategoryBars({
  items,
  total,
}: {
  items: { category: string; count: number }[]
  total: number
}) {
  const max = Math.max(...items.map((i) => i.count), 1)
  return (
    <ol className="flex flex-col gap-2.5">
      {items.map((tc, i) => (
        <li
          key={tc.category}
          className="grid grid-cols-[1.5rem_minmax(0,12rem)_minmax(0,1fr)_auto] items-center gap-3 text-sm"
        >
          <span className="font-mono text-xs text-muted-foreground">{i + 1}</span>
          <span className="truncate font-medium" title={tc.category}>
            {tc.category}
          </span>
          <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
            <span
              className="block h-full rounded-full bg-chart-1"
              style={{ width: `${Math.max(3, (tc.count / max) * 100)}%` }}
            />
          </span>
          <span className="text-right font-mono text-xs tabular-nums">
            {tc.count}
            {total > 0 ? (
              <span className="ml-1 text-muted-foreground">
                ({Math.round((tc.count / total) * 100)}%)
              </span>
            ) : null}
          </span>
        </li>
      ))}
    </ol>
  )
}

/** ≤5 cụm mới nổi — mảng rỗng thì ẨN CẢ KHỐI (spec UF-05 edge case). */
function EmergingSection({ items }: { items: EmergingClusterItem[] }) {
  if (items.length === 0) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Đang mới nổi</CardTitle>
        <CardDescription>Vấn đề mới xuất hiện hoặc tăng đột biến trong cửa sổ này.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col divide-y">
          {items.slice(0, 5).map((c) => (
            <li key={c.id}>
              <Link
                href={`/clusters?cluster=${c.id}`}
                className="flex flex-wrap items-center gap-2 py-2.5 text-sm transition-colors hover:text-signal"
              >
                <span className="min-w-0 flex-1 font-medium">{c.name}</span>
                {c.is_emerging ? <Badge variant="default">Mới nổi</Badge> : null}
                {c.is_spike ? <Badge variant="destructive">Tăng đột biến</Badge> : null}
                <span className="font-mono text-xs text-muted-foreground">
                  {c.feedback_count} phản hồi · {c.is_emerging ? "mới" : `${c.growth_ratio.toFixed(1)}×`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function ReportsInner() {
  const days = useDaysParam()
  const summary = useReportSummary(days)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Báo cáo tổng hợp"
        description={
          summary.data
            ? `Thống kê ${summary.data.window_days} ngày gần nhất · cập nhật ${formatDate(summary.data.generated_at)}`
            : `Thống kê ${days} ngày gần nhất`
        }
        actions={<TimeRangeToggle />}
      />

      {/* Đọc theo một mạch: tổng → phân rã theo mức độ/cảm xúc → chủ đề → cụm mới nổi. */}
      {summary.isPending ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </>
      ) : summary.isError ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>Chưa tải được báo cáo</EmptyTitle>
            <EmptyDescription>{summary.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <ReportTiles totals={summary.data.totals} />

          <div className="grid items-start gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Mức độ nghiêm trọng</CardTitle>
              </CardHeader>
              <CardContent>
                <SeverityBars bySeverity={summary.data.by_severity} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Cảm xúc</CardTitle>
              </CardHeader>
              <CardContent>
                <SentimentBars bySentiment={summary.data.by_sentiment} />
              </CardContent>
            </Card>
          </div>

          <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Chủ đề được nhắc nhiều nhất</CardTitle>
                <CardDescription>Top 10 · tỉ trọng trên tổng phản hồi</CardDescription>
              </CardHeader>
              <CardContent>
                {summary.data.top_categories.length === 0 ? (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>Chưa có chủ đề nào</EmptyTitle>
                      <EmptyDescription>
                        Chạy phân loại để gắn nhãn chủ đề cho phản hồi.
                      </EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                ) : (
                  <CategoryBars
                    items={summary.data.top_categories.slice(0, 10)}
                    total={summary.data.totals.feedback_count}
                  />
                )}
              </CardContent>
            </Card>
            <EmergingSection items={summary.data.emerging} />
          </div>
        </>
      )}
    </div>
  )
}

export default function ReportsSummaryPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <ReportsInner />
    </Suspense>
  )
}

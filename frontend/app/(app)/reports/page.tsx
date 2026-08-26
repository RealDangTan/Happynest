"use client"
import { Suspense } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { ReportTiles } from "@/components/report-tiles"
import { SeverityBars } from "@/components/severity-bars"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useReportSummary, type SummaryDays } from "@/hooks/use-reports"
import type { EmergingClusterItem } from "@/lib/types"
import { formatDate } from "@/lib/format"
import { SENTIMENT_LABEL } from "@/lib/labels"
import type { Sentiment } from "@/lib/types"

const DAY_OPTIONS: SummaryDays[] = [7, 30, 90]

/** Cảm xúc render THEO KEY THỰC TRẢ VỀ của server (4 key gồm mixed) —
 * không hardcode danh sách ô. Một hue duy nhất: phân bố, không phải thứ bậc. */
function SentimentBars({
  bySentiment,
}: {
  bySentiment: Record<string, number>
}) {
  const entries = Object.entries(bySentiment)
  const max = Math.max(...entries.map(([, v]) => v), 0)

  return (
    <div
      role="img"
      aria-label={`Phân bố cảm xúc: ${entries
        .map(([k, v]) => `${SENTIMENT_LABEL[k as Sentiment] ?? k} ${v}`)
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
            {SENTIMENT_LABEL[key as Sentiment] ?? key}
          </span>
        </div>
      ))}
    </div>
  )
}

/** ≤5 cụm mới nổi — mảng rỗng thì ẨN CẢ KHỐI (spec UF-05 edge case). */
function EmergingSection({ items }: { items: EmergingClusterItem[] }) {
  if (items.length === 0) return null
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-lg">Đang mới nổi</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.slice(0, 5).map((c) => (
          <Card key={c.id} className="transition-colors hover:bg-muted/50">
            <Link href="/clusters" aria-label={c.name}>
              <CardContent className="flex flex-col gap-1">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm leading-snug font-medium">
                    {c.name}
                  </span>
                  <span className="flex shrink-0 gap-1">
                    {c.is_emerging ? (
                      <Badge variant="default">Mới nổi</Badge>
                    ) : null}
                    {c.is_spike ? (
                      <Badge variant="destructive">Tăng đột biến</Badge>
                    ) : null}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {c.feedback_count} phản hồi ·{" "}
                  {c.is_emerging ? "Mới" : `${c.growth_ratio.toFixed(1)}×`}
                </span>
              </CardContent>
            </Link>
          </Card>
        ))}
      </div>
    </section>
  )
}

function ReportsInner() {
  const router = useRouter()
  const sp = useSearchParams()
  const rawDays = Number(sp.get("days"))
  const days: SummaryDays = DAY_OPTIONS.includes(rawDays as SummaryDays)
    ? (rawDays as SummaryDays)
    : 30
  const summary = useReportSummary(days)

  function setDays(v: string) {
    router.replace(`/reports?days=${v}`)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-heading text-2xl">Báo cáo tổng hợp</h1>
        <div className="ml-auto flex items-center gap-3">
          {summary.data ? (
            <span className="text-sm text-muted-foreground">
              Cập nhật lúc {formatDate(summary.data.generated_at)}
            </span>
          ) : null}
          <Select value={String(days)} onValueChange={setDays}>
            <SelectTrigger className="w-44" aria-label="Cửa sổ thời gian">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DAY_OPTIONS.map((d) => (
                <SelectItem key={d} value={String(d)}>
                  {d} ngày gần nhất
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Từng vùng skeleton độc lập — lỗi một vùng không che phần còn lại */}
      {summary.isPending ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </>
      ) : summary.isError ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Không tải được báo cáo</EmptyTitle>
            <EmptyDescription>{summary.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <p className="-mt-3 text-xs text-muted-foreground">
            Thống kê trên {summary.data.window_days} ngày gần nhất
          </p>

          <ReportTiles totals={summary.data.totals} />

          <div className="grid gap-4 md:grid-cols-2">
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

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top chủ đề</CardTitle>
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Chủ đề</TableHead>
                      <TableHead className="w-24 text-right">
                        Số lượng
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.top_categories.slice(0, 10).map((tc) => (
                      <TableRow key={tc.category}>
                        <TableCell className="font-medium">
                          {tc.category}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {tc.count}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <EmergingSection items={summary.data.emerging} />
        </>
      )}
    </div>
  )
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <ReportsInner />
    </Suspense>
  )
}

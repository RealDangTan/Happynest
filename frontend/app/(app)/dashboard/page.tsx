"use client"
import { Suspense } from "react"
import Link from "next/link"
import { ArrowRight, Upload } from "lucide-react"
import { useMe } from "@/hooks/use-me"
import { useReportSummary } from "@/hooks/use-reports"
import { FirstRunGuide } from "@/components/onboarding/first-run-guide"
import { PageHeader } from "@/components/page-header"
import type { EmergingClusterItem } from "@/lib/types"
import { ReportTiles } from "@/components/report-tiles"
import { SeverityBars } from "@/components/severity-bars"
import { TimeRangeToggle, useDaysParam } from "@/components/time-range-toggle"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/** ≤3 cụm đang nổi — rỗng thì ẩn khối (không mời đọc danh sách trống). */
function EmergingMini({ items }: { items: EmergingClusterItem[] }) {
  if (items.length === 0) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Đang nổi</CardTitle>
        <CardAction>
          <Button asChild size="sm" variant="ghost">
            <Link href="/clusters">Tất cả cụm</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        {items.slice(0, 3).map((c) => (
          <Link
            key={c.id}
            href={`/clusters?cluster=${c.id}`}
            className="flex items-center justify-between gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:bg-muted"
          >
            <span className="truncate">{c.name}</span>
            <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
              {c.is_spike ? <Badge variant="destructive">Tăng đột biến</Badge> : null}
              {c.feedback_count} phản hồi
            </span>
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}

function DashboardInner() {
  const me = useMe()
  // Dùng chung C4 + tham số ?days= với Báo cáo tổng hợp — số liệu khớp 1:1.
  const days = useDaysParam()
  const summary = useReportSummary(days)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`Xin chào${me.data ? `, ${me.data.email}` : ""}`}
        documentTitle="Tổng quan"
        actions={<TimeRangeToggle />}
      />

      <FirstRunGuide />

      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <Link href="/importer?new=1">
            <Upload data-icon="inline-start" />
            Nhập phản hồi
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/data-graph?ask=1">Hỏi AI về phản hồi</Link>
        </Button>
      </div>

      {summary.isPending ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </>
      ) : summary.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Chưa tải được tổng quan</AlertTitle>
          <AlertDescription className="flex flex-col gap-3">
            <span>{summary.error.message}</span>
            <div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => void summary.refetch()}
              >
                Thử lại
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {/* Cửa sổ đang xem không có phản hồi nào (dữ liệu cũ hơn) — nói rõ và
              đưa nút mở cửa sổ rộng hơn, thay vì để các ô 0 trông như lỗi. */}
          {summary.data.totals.feedback_count === 0 && days < 90 ? (
            <Alert>
              <AlertTitle>Không có phản hồi nào trong {days} ngày gần nhất</AlertTitle>
              <AlertDescription className="flex flex-col items-start gap-3">
                <span>Dữ liệu đã nhập có thể cũ hơn khoảng này. Mở rộng cửa sổ để xem.</span>
                <Button asChild size="sm" variant="outline">
                  <Link href="/dashboard?days=90">Xem 90 ngày</Link>
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}
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
            <EmergingMini items={summary.data.emerging} />
          </div>

          <Button asChild variant="ghost" size="sm" className="self-start">
            <Link href={`/reports/summary?days=${days}`}>
              Xem báo cáo tổng hợp {days} ngày
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        </>
      )}
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <DashboardInner />
    </Suspense>
  )
}

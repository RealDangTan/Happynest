"use client"
import Link from "next/link"
import { ClipboardList, PlayCircle } from "lucide-react"
import { useMe } from "@/hooks/use-me"
import { useReportSummary } from "@/hooks/use-reports"
import { FirstRunGuide } from "@/components/onboarding/first-run-guide"
import { PageHeader } from "@/components/page-header"
import type { EmergingClusterItem } from "@/lib/types"
import { ReportTiles } from "@/components/report-tiles"
import { SeverityBars } from "@/components/severity-bars"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/** ≤3 cụm đang nổi — rỗng thì ẩn khối (không mời đọc danh sách trống). */
function EmergingMini({ items }: { items: EmergingClusterItem[] }) {
  if (items.length === 0) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Đang nổi</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {items.slice(0, 3).map((c) => (
          <Link
            key={c.id}
            href="/clusters"
            className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted"
          >
            <span className="truncate">{c.name}</span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {c.feedback_count} phản hồi
            </span>
          </Link>
        ))}
        <Button asChild size="sm" variant="ghost" className="self-end">
          <Link href="/clusters">Xem tất cả cụm</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const me = useMe()
  // Dashboard dùng chung C4 với /reports (cùng queryKey days=30) — số liệu
  // khớp 1:1 và cache share giữa hai trang (spec Màn 4).
  const summary = useReportSummary(30)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`Xin chào${me.data ? `, ${me.data.email}` : ""}`}
        documentTitle="Tổng quan"
      />

      <FirstRunGuide />

      {/* Shortcut hành động */}
      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <Link href="/analysis">
            <PlayCircle data-icon="inline-start" />
            Chạy phân tích mới
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/feedbacks">
            <ClipboardList data-icon="inline-start" />
            Nhập / import phản hồi
          </Link>
        </Button>
      </div>

      {summary.isPending ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </>
      ) : summary.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Không tải được tổng quan</AlertTitle>
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

          <p className="text-xs text-muted-foreground">
            Số liệu 30 ngày gần nhất ·{" "}
            <Link href="/reports" className="underline underline-offset-2">
              xem báo cáo đầy đủ
            </Link>
          </p>
        </>
      )}
    </div>
  )
}

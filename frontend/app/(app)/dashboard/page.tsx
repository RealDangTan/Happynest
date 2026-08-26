"use client"
import Link from "next/link"
import { ClipboardList, PlayCircle } from "lucide-react"
import { useMe } from "@/hooks/use-me"
import { useReportSummary } from "@/hooks/use-reports"
import type { EmergingClusterItem } from "@/lib/types"
import { ReportTiles } from "@/components/report-tiles"
import { SeverityBars } from "@/components/severity-bars"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

const ROLE_LABEL = {
  pm: "Quản trị sản phẩm",
  operations: "Vận hành",
} as const

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

  const pending = summary.data?.totals.pending_review_count ?? 0

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-heading text-2xl">
          Xin chào{me.data ? `, ${me.data.email}` : ""}
        </h1>
        {me.data ? (
          <Badge variant="secondary">{ROLE_LABEL[me.data.role]}</Badge>
        ) : null}
      </div>

      {/* Shortcut hành động: chỉ mời làm việc khi CÓ việc (pending > 0) */}
      <div className="flex flex-wrap gap-2">
        {pending > 0 ? (
          <Button asChild>
            <Link href="/feedbacks?review_status=pending">
              <ClipboardList data-icon="inline-start" />
              Xử lý {pending} mục chờ duyệt
            </Link>
          </Button>
        ) : null}
        <Button asChild variant={pending > 0 ? "outline" : "default"}>
          <Link href="/analysis">
            <PlayCircle data-icon="inline-start" />
            Chạy phân tích mới
          </Link>
        </Button>
      </div>

      {summary.isPending ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-56 w-full" />
        </>
      ) : summary.isError ? null : (
        <>
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

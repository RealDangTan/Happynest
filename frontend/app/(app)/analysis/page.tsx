"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import { Suspense, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import {
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useLegacyTable,
  type LegacyColumnDef,
} from "@tanstack/react-table/legacy"
import { useRunProgress, useRunResults } from "@/hooks/use-analysis"
import type { Feedback } from "@/lib/types"
import { SEVERITY_LABEL } from "@/lib/labels"
import { useAppLang } from "@/lib/i18n"
import { formatDate } from "@/lib/format"
import {
  multiSelectFilterFn,
  severitySortFn,
} from "@/lib/table-sorts"
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  DataTableToolbar,
} from "@/components/data-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader } from "@/components/page-header"
import { useActivity } from "@/components/activity/activity-provider"

const STATUS_LABEL: Record<string, string> = {
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Thất bại",
}

function RunResults({ runId }: { runId: string }) {
  const lang = useAppLang()
  // Tải toàn bộ kết quả run (scope cap 100) — sort/filter/search client-side
  // trung thực trên cả run, không chỉ trang hiện tại.
  const results = useRunResults(runId)
  const rows = useMemo(() => results.data?.items ?? [], [results.data])

  const columns = useMemo<LegacyColumnDef<Feedback>[]>(
    () => [
      {
        id: "content",
        enableSorting: false,
        enableHiding: false,
        meta: { thClassName: "w-[45%]" },
        header: "Nội dung",
        cell: ({ row }) => (
          <Link href={`/feedbacks/${row.original.id}`} className="block">
            <span className="line-clamp-2">
              {row.original.feedback_text ?? "(trống)"}
            </span>
          </Link>
        ),
      },
      {
        id: "source",
        accessorFn: (f: Feedback) => f.source,
        meta: { label: "Nguồn" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Nguồn" />
        ),
        cell: ({ row }) => row.original.source,
      },
      {
        id: "severity",
        accessorFn: (f: Feedback) => f.ai_analysis?.severity ?? "",
        filterFn: multiSelectFilterFn,
        sortingFn: severitySortFn,
        sortDescFirst: true,
        meta: { label: "Mức độ" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Mức độ" />
        ),
        cell: ({ row }) => {
          const severity = row.original.ai_analysis?.severity
          return severity ? (
            <Badge
              variant={
                severity === "critical" || severity === "high"
                  ? "destructive"
                  : "secondary"
              }
            >
              {SEVERITY_LABEL[lang][severity]}
            </Badge>
          ) : (
            <span className="text-muted-foreground">…đang xử lý</span>
          )
        },
      },
      {
        id: "sentiment",
        accessorFn: (f: Feedback) => f.ai_analysis?.sentiment ?? "",
        enableSorting: false,
        filterFn: multiSelectFilterFn,
        meta: { label: "Cảm xúc" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Cảm xúc" />
        ),
        cell: ({ row }) => {
          const sentiment = row.original.ai_analysis?.sentiment
          return sentiment ? (
            <SentimentIndicator value={sentiment} />
          ) : (
            <span className="text-muted-foreground">…đang xử lý</span>
          )
        },
      },
      {
        id: "confidence",
        accessorFn: (f: Feedback) => f.ai_analysis?.confidence ?? -1,
        sortDescFirst: true,
        meta: { label: "Confidence", thClassName: "text-right", tdClassName: "text-right" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Confidence" className="justify-end" />
        ),
        cell: ({ row }) => {
          const confidence = row.original.ai_analysis?.confidence
          return confidence != null ? (
            <span className="tabular-nums">{`${Math.round(confidence * 100)}%`}</span>
          ) : (
            <span className="text-muted-foreground">…đang xử lý</span>
          )
        },
      },
    ],
    [lang],
  )

  const table = useLegacyTable({
    data: rows,
    columns,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    globalFilterFn: "includesString",
    initialState: {
      sorting: [{ id: "severity", desc: true }],
      pagination: { pageIndex: 0, pageSize: 20 },
    },
  })

  if (results.isPending)
    return (
      <CardContent className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </CardContent>
    )
  if (results.isError)
    return (
      <CardContent>
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Không tải được kết quả</EmptyTitle>
            <EmptyDescription>{results.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </CardContent>
    )

  return (
    <>
      <CardContent className="flex flex-col gap-3">
        <DataTableToolbar
          table={table}
          filters={[
            {
              columnId: "severity",
              title: "Mức độ",
              options: Object.entries(SEVERITY_LABEL[lang]).map(
                ([value, label]) => ({ value, label }),
              ),
            },
          ]}
        />
        <DataTable table={table} />
      </CardContent>
      <CardFooter className="border-t">
        <DataTablePagination table={table} />
      </CardFooter>
    </>
  )
}

function AnalysisInner() {
  const router = useRouter()
  const sp = useSearchParams()
  const runId = sp.get("run")
  const activity = useActivity()
  const progress = useRunProgress(runId)
  const [notified, setNotified] = useState<string | null>(null)

  // Toast tổng kết CHỈ 1 lần cho mỗi lần run đổi trạng thái kết thúc.
  useEffect(() => {
    const d = progress.data
    if (!d || d.status === "running" || notified === d.id) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot completion toast guard
    setNotified(d.id)
    if (d.status === "completed") {
      toast.success("Phân loại hoàn tất", {
        description: `${d.processed_count}/${d.total_count} phản hồi đã có nhãn.`,
      })
      router.refresh()
    }
  }, [progress.data, notified, router])

  const pct =
    progress.data && progress.data.total_count > 0
      ? Math.round(
          (progress.data.processed_count / progress.data.total_count) * 100
        )
      : 0

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Phân tích"
        description="Trang này giữ vai trò xem kết quả chi tiết — tạo run có scope và xem cost receipt trong Activity Center trên navbar."
        actions={
          <Button onClick={activity.openQueue}>Mở Activity Center</Button>
        }
      />

      {!runId ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>Chưa có lượt phân tích nào đang theo dõi</EmptyTitle>
            <EmptyDescription>
              Tạo run có scope trong Activity Center trên navbar, rồi mở kết quả
              chi tiết tại đây.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}

      {runId && progress.isPending ? (
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-16 w-full" />
          </CardContent>
        </Card>
      ) : null}

      {runId && progress.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Mất kết nối với server</AlertTitle>
          <AlertDescription>
            Không đọc được tiến độ run. Giữ nguyên trạng thái cuối cùng — hệ
            thống tự thử lại khi server phản hồi lại.
          </AlertDescription>
        </Alert>
      ) : null}

      {runId && progress.data ? (
        <Card>
          <CardHeader>
            <CardTitle>Tiến độ run</CardTitle>
            <CardDescription>
              {progress.data.id.slice(0, 8)} · bắt đầu{" "}
              {formatDate(progress.data.started_at)}
            </CardDescription>
            <CardAction>
              <Badge
                variant={
                  progress.data.status === "failed"
                    ? "destructive"
                    : "secondary"
                }
              >
                {STATUS_LABEL[progress.data.status]}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Progress value={pct} />
            <p className="text-sm text-muted-foreground">
              {progress.data.processed_count}/{progress.data.total_count} đã xử
              lý
            </p>
            {progress.data.status === "failed" ? (
              <Alert variant="destructive">
                <AlertTitle>Run thất bại</AlertTitle>
                <AlertDescription className="flex flex-col gap-3">
                  <span>
                    {progress.data.error ?? "Không rõ nguyên nhân."} Chạy lại sẽ
                    tạo run mới — chỉ phần chưa xử lý được nhặt, không nhân đôi
                    kết quả.
                  </span>
                  <div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={activity.openQueue}
                    >
                      Chọn lại scope trong Activity Center
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            ) : null}
            {progress.data.status === "completed" &&
            progress.data.total_count === 0 ? (
              <Alert>
                <AlertTitle>Không có gì mới</AlertTitle>
                <AlertDescription>
                  Không có feedback nào cần xử lý trong run này.
                </AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {runId ? (
        <Card>
          <CardHeader>
            <CardTitle>Kết quả của run</CardTitle>
            <CardDescription>
              Nhãn do LLM gán cho từng phản hồi — bấm vào nội dung để mở chi
              tiết.
            </CardDescription>
          </CardHeader>
          <RunResults runId={runId} />
        </Card>
      ) : null}
    </div>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <AnalysisInner />
    </Suspense>
  )
}

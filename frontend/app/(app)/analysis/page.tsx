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
import { useRunProgress, useRunResults, useRuns } from "@/hooks/use-analysis"
import type { Feedback } from "@/lib/types"
import { SEVERITY_LABEL } from "@/lib/labels"
import { useAppLang } from "@/lib/i18n"
import { formatDate, formatRelative } from "@/lib/format"
import { runDuration, runScopeLabel } from "@/lib/run-format"
import { RUN_STATUS_TONE, SEVERITY_TONE } from "@/lib/tone"
import { cn } from "@/lib/utils"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/page-header"
import { useActivity } from "@/components/activity/activity-provider"

const STATUS_LABEL: Record<string, string> = {
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Thất bại",
  cancelled: "Đã dừng",
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
            <Badge variant={SEVERITY_TONE[severity] ?? "secondary"}>
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
        meta: { label: "Độ tin cậy", thClassName: "text-right", tdClassName: "text-right" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Độ tin cậy" className="justify-end" />
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

/** Lịch sử lượt chạy (mẫu Databricks "Job runs"): trạng thái, thời lượng và
 * kết quả trên từng dòng; bấm dòng để mở chi tiết lượt đó ngay bên cạnh. */
function RunHistory({
  selectedId,
  compact,
  onSelect,
}: {
  selectedId: string | null
  compact: boolean
  onSelect: (id: string) => void
}) {
  const runs = useRuns()
  const items = (runs.data?.items ?? []).filter((r) => r.import_id != null)
  return (
    <Card size="sm" className={cn("min-w-0", compact && "self-start xl:sticky xl:top-20")}>
      <CardHeader>
        <CardTitle>Lịch sử lượt chạy</CardTitle>
        <CardDescription>
          {runs.isPending ? "Đang tải…" : `${items.length} lượt phân loại gần nhất`}
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        {runs.isPending ? (
          <div className="flex flex-col gap-2 px-(--card-spacing)">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="px-(--card-spacing) text-sm text-muted-foreground">
            Chưa có lượt phân loại nào. Mở Kho phản hồi để chạy lượt đầu tiên.
          </p>
        ) : (
          <div className={cn("overflow-auto", compact && "max-h-[65vh]")}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-(--card-spacing)">Lượt</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  {compact ? null : <TableHead>Bắt đầu</TableHead>}
                  <TableHead className="text-right">Thời lượng</TableHead>
                  {compact ? null : <TableHead className="pr-(--card-spacing) text-right">Kết quả</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((run) => (
                  <TableRow
                    key={run.id}
                    data-state={run.id === selectedId ? "selected" : undefined}
                    className="cursor-pointer"
                    onClick={() => onSelect(run.id)}
                  >
                    <TableCell className="pl-(--card-spacing)">
                      <button
                        type="button"
                        className="flex flex-col text-left focus-visible:outline-2 focus-visible:outline-ring"
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelect(run.id)
                        }}
                      >
                        <span className="font-mono text-xs">{run.id.slice(0, 8)}</span>
                        <span className="text-xs text-muted-foreground">{runScopeLabel(run)}</span>
                      </button>
                    </TableCell>
                    <TableCell>
                      <Badge variant={RUN_STATUS_TONE[run.status] ?? "secondary"}>
                        {STATUS_LABEL[run.status] ?? run.status}
                      </Badge>
                    </TableCell>
                    {compact ? null : (
                      <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
                        {formatRelative(run.started_at)}
                      </TableCell>
                    )}
                    <TableCell className="text-right font-mono text-xs whitespace-nowrap">
                      {runDuration(run)}
                    </TableCell>
                    {compact ? null : (
                      <TableCell className="pr-(--card-spacing) text-right font-mono text-xs whitespace-nowrap">
                        {run.processed_count}/{run.total_count}
                        {run.failed_count > 0 ? (
                          <span className="ml-1 text-destructive">· {run.failed_count} lỗi</span>
                        ) : null}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
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

  const selectRun = (id: string) => router.replace(`/analysis?run=${id}`, { scroll: false })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Phân tích"
        description="Lịch sử các lượt phân loại và nhãn AI gán cho từng phản hồi."
        actions={
          <Button variant="outline" onClick={activity.openQueue}>Mở Trung tâm hoạt động</Button>
        }
      />

      <div className={cn("grid min-w-0 items-start gap-6", runId && "xl:grid-cols-[minmax(18rem,24rem)_minmax(0,1fr)]")}>
      <RunHistory selectedId={runId} compact={Boolean(runId)} onSelect={selectRun} />

      {runId ? (
      <div className="flex min-w-0 flex-col gap-6">

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
            <CardTitle>Lượt {progress.data.id.slice(0, 8)}</CardTitle>
            <CardDescription>
              {runScopeLabel(progress.data)} · bắt đầu {formatDate(progress.data.started_at)} · {runDuration(progress.data)}
            </CardDescription>
            <CardAction>
              <Badge variant={RUN_STATUS_TONE[progress.data.status] ?? "secondary"}>
                {STATUS_LABEL[progress.data.status]}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Progress value={pct} />
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
              <div><dt className="text-xs text-muted-foreground">Đã xử lý</dt><dd className="font-mono">{progress.data.processed_count}/{progress.data.total_count}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Lỗi</dt><dd className="font-mono">{progress.data.failed_count}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Mô hình</dt><dd className="truncate font-mono text-xs leading-5" title={progress.data.llm_model}>{progress.data.llm_model}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Phiên bản prompt</dt><dd className="truncate font-mono text-xs leading-5">{progress.data.prompt_version}</dd></div>
            </dl>
            {progress.data.status === "failed" ? (
              <Alert variant="destructive">
                <AlertTitle>Lượt chạy thất bại</AlertTitle>
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
                      Chọn lại phạm vi trong Trung tâm hoạt động
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
                  Không có phản hồi nào cần xử lý trong lượt này.
                </AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {runId ? (
        <Card>
          <CardHeader>
            <CardTitle>Kết quả của lượt</CardTitle>
            <CardDescription>
              Nhãn AI gán cho từng phản hồi — bấm vào nội dung để mở chi tiết.
            </CardDescription>
          </CardHeader>
          <RunResults runId={runId} />
        </Card>
      ) : null}
      </div>
      ) : null}
      </div>
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

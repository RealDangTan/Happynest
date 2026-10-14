"use client"
import { Suspense, useEffect, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import {
  useRunProgress,
  useRunResults,
  RUN_RESULTS_PAGE_SIZE,
} from "@/hooks/use-analysis"
import type { Feedback } from "@/lib/types"
import { SENTIMENT_LABEL, SEVERITY_LABEL } from "@/lib/labels"
import { formatDate } from "@/lib/format"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
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
  const [page, setPage] = useState(1)
  const results = useRunResults(runId, page)
  const total = results.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / RUN_RESULTS_PAGE_SIZE))

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
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[45%]">Nội dung</TableHead>
              <TableHead>Nguồn</TableHead>
              <TableHead>Mức độ</TableHead>
              <TableHead>Cảm xúc</TableHead>
              <TableHead>Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.data.items.map((fb: Feedback) => {
              const ai = fb.ai_analysis
              return (
                <TableRow key={fb.id} className="cursor-pointer">
                  <TableCell className="max-w-md">
                    <Link href={`/feedbacks/${fb.id}`} className="block">
                      <span className="line-clamp-2">
                        {fb.feedback_text ?? "(trống)"}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell>{fb.source}</TableCell>
                  <TableCell>
                    {ai?.severity ? (
                      <Badge
                        variant={
                          ai.severity === "critical" || ai.severity === "high"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {SEVERITY_LABEL[ai.severity]}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">…đang xử lý</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {ai?.sentiment ? (
                      SENTIMENT_LABEL[ai.sentiment]
                    ) : (
                      <span className="text-muted-foreground">…đang xử lý</span>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {ai?.confidence != null ? (
                      `${Math.round(ai.confidence * 100)}%`
                    ) : (
                      <span className="text-muted-foreground">…đang xử lý</span>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
      <CardFooter className="justify-between border-t">
        <span className="text-sm text-muted-foreground">
          {total} item · trang {page}/{totalPages}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Trước
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau
          </Button>
        </div>
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

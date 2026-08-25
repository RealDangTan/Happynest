"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Play, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import {
  useRunProgress,
  useRunResults,
  useTriggerRun,
  RUN_RESULTS_PAGE_SIZE,
} from "@/hooks/use-analysis";
import type { Feedback } from "@/lib/types";
import {
  AI_ISSUE_LABEL,
  REVIEW_LABEL,
  SENTIMENT_LABEL,
  SEVERITY_LABEL,
} from "@/lib/labels";
import { formatDate } from "@/lib/format";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

const STATUS_LABEL: Record<string, string> = {
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Thất bại",
};

function TriggerButton({
  running,
  onConfirm,
}: {
  running: boolean;
  onConfirm: () => void;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button disabled={running}>
          <Play data-icon="inline-start" />
          Chạy phân loại
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Chạy trên toàn bộ feedback chưa xử lý?</AlertDialogTitle>
          <AlertDialogDescription>
            Batch sẽ phân loại + tạo embedding cho mọi phản hồi chưa có run. Hành
            động tốn LLM credit; các run song song không trùng công việc (claim
            theo row).
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Huỷ</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Xác nhận chạy</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function RunResults({ runId }: { runId: string }) {
  const [page, setPage] = useState(1);
  const results = useRunResults(runId, page);
  const total = results.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / RUN_RESULTS_PAGE_SIZE));

  if (results.isPending)
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  if (results.isError)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Không tải được kết quả</EmptyTitle>
          <EmptyDescription>{results.error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );

  return (
    <div className="flex flex-col gap-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[45%]">Nội dung</TableHead>
            <TableHead>Nguồn</TableHead>
            <TableHead>Mức độ</TableHead>
            <TableHead>Duyệt</TableHead>
            <TableHead>Cảm xúc</TableHead>
            <TableHead>AI issue</TableHead>
            <TableHead>Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.data.items.map((fb: Feedback) => (
            <TableRow key={fb.id} className="cursor-pointer">
              <TableCell className="max-w-md">
                <Link href={`/feedbacks/${fb.id}`} className="block">
                  <span className="line-clamp-2">
                    {fb.sanitized_content ?? "(trống)"}
                  </span>
                </Link>
              </TableCell>
              <TableCell>{fb.source}</TableCell>
              <TableCell>
                {fb.severity ? (
                  <Badge
                    variant={
                      fb.severity === "critical" || fb.severity === "high"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {SEVERITY_LABEL[fb.severity]}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">…đang xử lý</span>
                )}
              </TableCell>
              <TableCell>
                <Badge variant="outline">{REVIEW_LABEL[fb.review_status]}</Badge>
              </TableCell>
              <TableCell>
                {fb.sentiment ? (
                  SENTIMENT_LABEL[fb.sentiment]
                ) : (
                  <span className="text-muted-foreground">…đang xử lý</span>
                )}
              </TableCell>
              <TableCell>
                {fb.ai_issue ? (
                  AI_ISSUE_LABEL[fb.ai_issue]
                ) : (
                  <span className="text-muted-foreground">…đang xử lý</span>
                )}
              </TableCell>
              <TableCell className="whitespace-nowrap">
                {fb.confidence != null
                  ? `${Math.round(fb.confidence * 100)}%`
                  : (
                    <span className="text-muted-foreground">…đang xử lý</span>
                  )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex items-center justify-between">
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
      </div>
    </div>
  );
}

function AnalysisInner() {
  const router = useRouter();
  const sp = useSearchParams();
  const runId = sp.get("run");
  const trigger = useTriggerRun();
  const progress = useRunProgress(runId);
  const [notified, setNotified] = useState<string | null>(null);

  // Toast tổng kết CHỈ 1 lần cho mỗi lần run đổi trạng thái kết thúc.
  useEffect(() => {
    const d = progress.data;
    if (!d || d.status === "running" || notified === d.id) return;
    setNotified(d.id);
    if (d.status === "completed") {
      toast.success("Phân loại hoàn tất", {
        description: `${d.processed_count}/${d.total_count} phản hồi đã có nhãn.`,
      });
      router.refresh();
    }
  }, [progress.data, notified, router]);

  function startRun() {
    trigger.mutate(undefined, {
      onSuccess: (r) =>
        router.replace(`/analysis?run=${r.run_id}`),
    });
  }

  const pct =
    progress.data && progress.data.total_count > 0
      ? Math.round(
          (progress.data.processed_count / progress.data.total_count) * 100,
        )
      : 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl">Phân tích</h1>
        <TriggerButton
          running={progress.data?.status === "running"}
          onConfirm={startRun}
        />
      </div>

      {!runId ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Chưa có lượt phân tích nào đang theo dõi</EmptyTitle>
            <EmptyDescription>
              Bấm “Chạy phân loại” để xử lý hàng loạt các phản hồi chưa có nhãn:
              hệ thống gọi LLM phân loại (mức độ, cảm xúc, vấn đề AI) và tạo
              embedding cho tìm kiếm tương tự.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}

      {trigger.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Không tạo được run</AlertTitle>
          <AlertDescription>{trigger.error.message}</AlertDescription>
        </Alert>
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
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle>Tiến độ run</CardTitle>
                <CardDescription>
                  {progress.data.id.slice(0, 8)} · bắt đầu{" "}
                  {formatDate(progress.data.started_at)}
                </CardDescription>
              </div>
              <Badge
                variant={
                  progress.data.status === "failed" ? "destructive" : "secondary"
                }
              >
                {STATUS_LABEL[progress.data.status]}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Progress value={pct} />
            <p className="text-sm text-muted-foreground">
              {progress.data.processed_count}/{progress.data.total_count} đã xử lý
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
                    <Button size="sm" variant="outline" onClick={startRun}>
                      <RefreshCw data-icon="inline-start" />
                      Chạy lại phần còn lại
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
        <section className="flex flex-col gap-3">
          <h2 className="font-heading text-lg">Kết quả của run</h2>
          <RunResults runId={runId} />
        </section>
      ) : null}
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <AnalysisInner />
    </Suspense>
  );
}

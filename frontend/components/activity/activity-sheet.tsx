"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Ban,
  Clock3,
  FileSpreadsheet,
  Maximize2,
  Play,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useCancelImport, useImport } from "@/hooks/use-imports";
import { useAnalysisPreview, useCancelRun, useRunProgress, useTriggerRun } from "@/hooks/use-analysis";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnalysisScope, FeedbackListResponse, ImportRecord, RunProgress } from "@/lib/types";
import {
  IMPORT_STEPS,
  StepMapping,
  StepPreview,
  StepResult,
  stepForImport,
} from "@/components/importer/import-steps";
import { Stepper } from "@/components/stepper";
import { useActivity } from "./activity-provider";

const ATTENTION = new Set(["profile_ready", "mapping_review", "failed"]);
const IMPORT_RUNNING = new Set(["mapping_generating", "importing"]);

const STATUS_LABEL: Record<string, string> = {
  profile_ready: "Chờ tạo mapping",
  mapping_generating: "AI đang tạo mapping",
  mapping_review: "Chờ duyệt mapping",
  importing: "Đang import",
  imported: "Đã import",
  failed: "Thất bại",
  cancelled: "Đã hủy",
  running: "Đang phân tích",
  completed: "Đã phân tích",
};

function statusBadge(status: string) {
  return (
    <Badge variant={status === "failed" ? "destructive" : "secondary"}>
      {STATUS_LABEL[status] ?? status}
    </Badge>
  );
}

/** Nút chuyển task sang trang đầy đủ — Sheet chỉ đủ chỗ cho việc xem nhanh,
 * duyệt mapping bảng 4 cột cần cả màn /importer. */
function OpenFullPageButton({ href }: { href: string }) {
  return (
    <Button variant="outline" size="sm" asChild>
      <Link href={href}>
        <Maximize2 data-icon="inline-start" />
        Toàn màn hình
      </Link>
    </Button>
  );
}

function ImportActivityRow({ item }: { item: ImportRecord }) {
  const { openImport } = useActivity();
  return (
    <button className="flex w-full items-center gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-accent" onClick={() => openImport(item.id)}>
      <FileSpreadsheet className="size-4 text-muted-foreground" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{item.original_filename ?? `Import ${item.id.slice(0, 8)}`}</span>
        <span className="text-xs text-muted-foreground">{item.source_row_count ?? item.row_count ?? 0} dòng</span>
      </span>
      {statusBadge(item.status)}
    </button>
  );
}

function RunActivityRow({ run }: { run: RunProgress }) {
  const { openRun } = useActivity();
  return (
    <button className="flex w-full items-center gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-accent" onClick={() => openRun(run.id)}>
      <Play className="size-4 text-muted-foreground" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">Phân tích {run.mode === "batch" ? "toàn bộ import" : "feedback đã chọn"}</span>
        <span className="text-xs text-muted-foreground">{run.processed_count}/{run.total_count} feedback</span>
      </span>
      {statusBadge(run.status)}
    </button>
  );
}

function ActivityQueue() {
  const { imports, runs } = useActivity();
  const scopedRuns = runs.filter(
    (run) => run.import_id && (run.mode === "selected" || run.mode === "batch"),
  );
  const attention = imports.filter((item) => ATTENTION.has(item.status));
  const runningImports = imports.filter((item) => IMPORT_RUNNING.has(item.status));
  const runningRuns = scopedRuns.filter((run) => run.status === "running");
  const recentImports = imports.filter((item) => ["imported", "cancelled"].includes(item.status));
  const recentRuns = scopedRuns.filter((run) => ["completed", "failed", "cancelled"].includes(run.status));

  const empty = (text: string) => (
    <Empty className="min-h-48 border">
      <EmptyHeader><EmptyTitle>Chưa có hoạt động</EmptyTitle><EmptyDescription>{text}</EmptyDescription></EmptyHeader>
    </Empty>
  );

  return (
    <Tabs defaultValue={attention.length ? "attention" : runningImports.length + runningRuns.length ? "running" : "recent"} className="mt-4">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="attention">Cần xử lý ({attention.length})</TabsTrigger>
        <TabsTrigger value="running">Đang chạy ({runningImports.length + runningRuns.length})</TabsTrigger>
        <TabsTrigger value="recent">Gần đây</TabsTrigger>
      </TabsList>
      <TabsContent value="attention" className="space-y-2">
        {attention.length ? attention.map((item) => <ImportActivityRow key={item.id} item={item} />) : empty("Upload CSV từ trang Phản hồi để bắt đầu.")}
      </TabsContent>
      <TabsContent value="running" className="space-y-2">
        {runningImports.map((item) => <ImportActivityRow key={item.id} item={item} />)}
        {runningRuns.map((run) => <RunActivityRow key={run.id} run={run} />)}
        {!runningImports.length && !runningRuns.length ? empty("Không có job nào đang dùng provider.") : null}
      </TabsContent>
      <TabsContent value="recent" className="space-y-2">
        {recentImports.slice(0, 10).map((item) => <ImportActivityRow key={item.id} item={item} />)}
        {recentRuns.slice(0, 10).map((run) => <RunActivityRow key={run.id} run={run} />)}
        {!recentImports.length && !recentRuns.length ? empty("Lịch sử gần đây sẽ xuất hiện tại đây.") : null}
      </TabsContent>
    </Tabs>
  );
}

function AnalysisChooser({ item }: { item: ImportRecord }) {
  const activity = useActivity();
  const qc = useQueryClient();
  const [mode, setMode] = useState<"selected" | "batch">("batch");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const preview = useAnalysisPreview();
  const trigger = useTriggerRun();
  const feedbacks = useQuery({
    queryKey: ["feedbacks", "import", item.id, "pending"],
    enabled: item.status === "imported",
    queryFn: () => apiFetch<FeedbackListResponse>(`/api/feedbacks?import_id=${item.id}&analysis_state=pending&limit=100`),
  });
  if (item.status !== "imported") return null;
  const rows = feedbacks.data?.items ?? [];
  const scope: AnalysisScope = mode === "batch" ? { mode, import_id: item.id } : { mode, import_id: item.id, feedback_ids: [...selected] };
  const requestPreview = () => preview.mutate(scope);
  const start = () => {
    if (!preview.data) return;
    trigger.mutate({ scope, confirmedItemCount: preview.data.selected_count }, {
      onSuccess: ({ run_id }) => { void qc.invalidateQueries({ queryKey: ["feedbacks"] }); activity.openRun(run_id); },
      onError: (error) => toast.error(error instanceof ApiError ? error.message : "Không tạo được run"),
    });
  };
  return (
    <section className="space-y-4 rounded-xl border p-4">
      <div><h3 className="font-heading text-base">Chạy phân tích cho lô này</h3><p className="text-sm text-muted-foreground">Không tự chạy sau import. Mỗi run tối đa 100 feedback.</p></div>
      <ToggleGroup type="single" value={mode} onValueChange={(value) => { if (value) { setMode(value as "selected" | "batch"); preview.reset(); } }} variant="outline" className="justify-start">
        <ToggleGroupItem value="selected">Chọn từng mục</ToggleGroupItem><ToggleGroupItem value="batch">Chạy theo lô</ToggleGroupItem>
      </ToggleGroup>
      {mode === "selected" ? <div className="max-h-64 overflow-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead className="w-10" /><TableHead>Feedback chờ xử lý</TableHead></TableRow></TableHeader><TableBody>{rows.map((row) => <TableRow key={row.id}><TableCell><Checkbox checked={selected.has(row.id)} onCheckedChange={(checked) => { preview.reset(); setSelected((old) => { const next = new Set(old); if (checked) next.add(row.id); else next.delete(row.id); return next; }); }} /></TableCell><TableCell className="max-w-md"><span className="line-clamp-2">{row.feedback_text}</span></TableCell></TableRow>)}</TableBody></Table></div> : <Alert><Clock3 className="size-4" /><AlertTitle>Tối đa 100 / {feedbacks.data?.total ?? 0} pending</AlertTitle><AlertDescription>Phân loại singular: mỗi feedback một gọi JEV riêng (~1s), embedding đi cùng từng mục.</AlertDescription></Alert>}
      <Button variant="outline" onClick={requestPreview} disabled={preview.isPending || (mode === "selected" && selected.size === 0)}>{preview.isPending ? <Spinner data-icon="inline-start" /> : null}Tính cost receipt</Button>
      {preview.data ? <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted p-3 text-sm sm:grid-cols-3"><span><strong>{preview.data.selected_count}</strong><br />feedback</span><span><strong>{preview.data.logical_classify_requests}</strong><br />classify calls</span><span><strong>{preview.data.logical_embedding_requests}</strong><br />embed calls</span><span><strong>{preview.data.max_provider_attempts}</strong><br />attempts tối đa</span><span><strong>~{preview.data.estimated_input_tokens}</strong><br />input tokens</span><span><strong>{preview.data.remaining_count}</strong><br />còn lại</span></div> : null}
      {preview.data ? <AlertDialog><AlertDialogTrigger asChild><Button><Play data-icon="inline-start" />Xác nhận phân tích</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Chạy paid analysis theo receipt?</AlertDialogTitle><AlertDialogDescription>{preview.data.selected_count} feedback, {preview.data.logical_classify_requests + preview.data.logical_embedding_requests} logical calls, tối đa {preview.data.max_provider_attempts} provider attempts. Scope không đổi sẽ được claim atomically.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Quay lại</AlertDialogCancel><AlertDialogAction onClick={start}>Xác nhận chạy</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog> : null}
    </section>
  );
}

function ImportDetail({ id }: { id: string }) {
  const { openQueue } = useActivity();
  const detail = useImport(id);
  const cancel = useCancelImport();
  const item = detail.data;
  const step = item ? stepForImport(item) : null;
  const cancellable = Boolean(item && ["profile_ready", "failed"].includes(item.status));
  return (
    <div className="mt-4 space-y-4">
      <Button variant="ghost" size="sm" onClick={openQueue}><ArrowLeft data-icon="inline-start" />Hàng chờ</Button>
      {detail.isPending ? <Spinner /> : null}
      {item ? (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="font-heading text-xl">{item.original_filename ?? "CSV import"}</h2>
              <p className="truncate text-sm text-muted-foreground">{item.id}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {statusBadge(item.status)}
              <OpenFullPageButton href={`/importer?import=${item.id}`} />
              {cancellable ? (
                <Button variant="ghost" size="sm" disabled={cancel.isPending} onClick={() => cancel.mutate(item.id)}>
                  <Ban data-icon="inline-start" />Hủy import
                </Button>
              ) : null}
            </div>
          </div>
          <Stepper steps={IMPORT_STEPS} current={step ?? "Preview"} label="Import steps" />
          {step === "Preview" ? <StepPreview importId={item.id} /> : null}
          {step === "Mapping" ? <StepMapping importId={item.id} /> : null}
          {step === "Result" ? <StepResult importId={item.id} /> : null}
          <AnalysisChooser item={item} />
        </>
      ) : (
        <Alert variant="destructive"><AlertTitle>Không tải được import</AlertTitle><AlertDescription>{detail.error?.message}</AlertDescription></Alert>
      )}
    </div>
  );
}

function RunDetail({ id }: { id: string }) {
  const { openQueue } = useActivity();
  const run = useRunProgress(id);
  const cancel = useCancelRun();
  const data = run.data;
  const pct = data?.total_count ? Math.round((data.processed_count / data.total_count) * 100) : 0;
  return <div className="mt-4 space-y-4"><Button variant="ghost" size="sm" onClick={openQueue}><ArrowLeft data-icon="inline-start" />Hàng chờ</Button>{data ? <><div className="flex flex-wrap items-start justify-between gap-3"><h2 className="font-heading text-xl">Analysis run</h2><div className="flex shrink-0 items-center gap-2">{statusBadge(data.status)}<OpenFullPageButton href={`/analysis?run=${id}`} /></div></div><section className="space-y-3 rounded-xl border p-4"><Progress value={pct} /><p className="text-sm">{data.processed_count}/{data.total_count} hoàn tất · {data.failed_count} lỗi</p><p className="text-xs text-muted-foreground">Phân loại từng mục (JEV per-item) · Dừng có hiệu lực sau mục hiện tại.</p><div className="flex flex-wrap gap-2">{data.status === "running" ? <Button variant="outline" disabled={cancel.isPending || Boolean(data.cancel_requested_at)} onClick={() => cancel.mutate(id)}><Ban data-icon="inline-start" />{data.cancel_requested_at ? "Đang chờ dừng" : "Dừng run"}</Button> : null}<Button variant="outline" asChild><Link href={`/analysis?run=${id}`}>Xem kết quả chi tiết</Link></Button></div>{data.error ? <Alert variant="destructive"><TriangleAlert className="size-4" /><AlertTitle>Có lỗi</AlertTitle><AlertDescription>{data.error}</AlertDescription></Alert> : null}</section></> : <Spinner />}</div>;
}

export function ActivitySheet() {
  const activity = useActivity();
  const param = activity.activityParam;
  const detail = param?.startsWith("import:") ? <ImportDetail id={param.slice(7)} /> : param?.startsWith("run:") ? <RunDetail id={param.slice(4)} /> : <ActivityQueue />;
  return (
    <Sheet open={Boolean(param)} onOpenChange={(open) => { if (!open) activity.closeActivity(); }}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-4xl">
        <SheetHeader><SheetTitle>Activity Center</SheetTitle><SheetDescription>Duyệt mapping, import và chạy AI có budget guard — task lớn mở toàn màn hình để xử lý.</SheetDescription></SheetHeader>
        <div className="px-4 pb-6">{detail}</div>
      </SheetContent>
    </Sheet>
  );
}

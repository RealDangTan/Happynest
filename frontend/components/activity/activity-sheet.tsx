"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Ban, CheckCircle2, Clock3, FileSpreadsheet, Play, TriangleAlert } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  useCancelImport,
  useDecideMapping,
  useGetMapping,
  useImport,
  useImportPreview,
  useProposeMapping,
} from "@/hooks/use-imports";
import { useAnalysisPreview, useCancelRun, useRunProgress, useTriggerRun } from "@/hooks/use-analysis";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnalysisScope, FeedbackListResponse, HumanMappingAction, ImportRecord, MappingDecision, MappingItem, RunProgress } from "@/lib/types";
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
        <span className="block text-sm font-medium">Phân tích {run.mode === "batch" ? "theo lô" : "từng mục"}</span>
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

function ProfilePreview({ importId }: { importId: string }) {
  const preview = useImportPreview(importId);
  if (preview.isPending) return <Spinner />;
  if (!preview.data) return null;
  return (
    <section className="space-y-3 rounded-xl border bg-muted/20 p-4">
      <div className="flex items-center justify-between"><h3 className="font-heading text-base">1. Preview cấu trúc</h3><Badge variant="outline">Chưa gọi AI</Badge></div>
      <p className="text-sm text-muted-foreground">{preview.data.source_row_count} dòng · sample đã sanitize trước khi lưu.</p>
      <Table>
        <TableHeader><TableRow><TableHead>Cột</TableHead><TableHead>Kiểu</TableHead><TableHead>Sample an toàn</TableHead></TableRow></TableHeader>
        <TableBody>{preview.data.column_profiles.map((column) => (
          <TableRow key={column.name}><TableCell className="font-medium">{column.name}</TableCell><TableCell>{column.detected_type ?? "—"}</TableCell><TableCell className="max-w-xs truncate text-muted-foreground">{column.sample_values?.join(" · ") || "—"}</TableCell></TableRow>
        ))}</TableBody>
      </Table>
    </section>
  );
}

function MappingGate({ item }: { item: ImportRecord }) {
  const propose = useProposeMapping();
  const cancel = useCancelImport();
  if (!["profile_ready", "mapping_generating", "failed"].includes(item.status)) return null;
  if (item.status === "mapping_generating") return <Alert><Spinner data-icon="inline-start" /><AlertTitle>AI đang tạo mapping</AlertTitle><AlertDescription>Job đã được claim. Có thể đóng Sheet; tiến độ vẫn được giữ.</AlertDescription></Alert>;
  return (
    <section className="space-y-3 rounded-xl border p-4">
      <h3 className="font-heading text-base">2. Tạo đề xuất mapping</h3>
      {item.error ? <Alert variant="destructive"><AlertTitle>Lần trước thất bại</AlertTitle><AlertDescription>{item.error}</AlertDescription></Alert> : null}
      <div className="rounded-lg bg-muted p-3 text-sm"><p>Receipt: 1 logical mapping job</p><p className="text-muted-foreground">Tối đa 3 provider attempts theo fallback structured output.</p></div>
      <div className="flex gap-2">
        <AlertDialog>
          <AlertDialogTrigger asChild><Button><Play data-icon="inline-start" />Tạo mapping bằng AI</Button></AlertDialogTrigger>
          <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Xác nhận paid mapping job?</AlertDialogTitle><AlertDialogDescription>AI chỉ nhận profile/sample đã sanitize, không nhận file CSV raw. Job được chống double-click và có thể retry nếu kẹt quá 5 phút.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Quay lại</AlertDialogCancel><AlertDialogAction onClick={() => propose.mutate(item.id)}>Xác nhận chạy</AlertDialogAction></AlertDialogFooter></AlertDialogContent>
        </AlertDialog>
        <Button variant="ghost" disabled={cancel.isPending} onClick={() => cancel.mutate(item.id)}><Ban data-icon="inline-start" />Hủy import</Button>
      </div>
    </section>
  );
}

function MappingReview({ item }: { item: ImportRecord }) {
  const mapping = useGetMapping(item.status === "mapping_review" ? item.id : null);
  const decide = useDecideMapping();
  const [actions, setActions] = useState<Record<string, { action: HumanMappingAction; targetKey?: string }>>({});
  if (item.status !== "mapping_review") return null;
  if (mapping.isPending) return <Spinner />;
  const mappings = mapping.data?.mappings ?? [];
  const defaultAction = (entry: MappingItem): HumanMappingAction => entry.decision === "AMBIGUOUS" ? "ignore" : "approve";
  const submit = () => {
    const decisions: MappingDecision[] = mappings.map((entry) => ({
      source_field: entry.source_field,
      action: actions[entry.source_field]?.action ?? defaultAction(entry),
      ...(actions[entry.source_field]?.targetKey ? { target_key: actions[entry.source_field].targetKey } : {}),
    }));
    decide.mutate({ importId: item.id, decisions }, { onError: (error) => toast.error(error instanceof ApiError ? error.message : "Không import được") });
  };
  return (
    <section className="space-y-3 rounded-xl border p-4">
      <h3 className="font-heading text-base">3. Xác nhận mapping AI</h3>
      <Table><TableHeader><TableRow><TableHead>Cột CSV</TableHead><TableHead>AI đề xuất</TableHead><TableHead>Quyết định</TableHead></TableRow></TableHeader><TableBody>{mappings.map((entry) => {
        const current = actions[entry.source_field]?.action ?? defaultAction(entry);
        return <TableRow key={entry.source_field}><TableCell className="font-medium">{entry.source_field}</TableCell><TableCell><span className="block">{entry.decision}{entry.target ? ` → ${entry.target}` : ""}</span><span className="text-xs text-muted-foreground">{entry.reason}</span></TableCell><TableCell><Select value={current} onValueChange={(value) => setActions((old) => ({ ...old, [entry.source_field]: { action: value as HumanMappingAction, targetKey: old[entry.source_field]?.targetKey } }))}><SelectTrigger className="w-40"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="approve">Duyệt đề xuất</SelectItem><SelectItem value="remap">Map field khác</SelectItem><SelectItem value="demote">Source metadata</SelectItem><SelectItem value="ignore">Bỏ qua</SelectItem></SelectContent></Select>{current === "remap" ? <Input className="mt-2" placeholder="target_key" value={actions[entry.source_field]?.targetKey ?? ""} onChange={(event) => setActions((old) => ({ ...old, [entry.source_field]: { action: "remap", targetKey: event.target.value } }))} /> : null}</TableCell></TableRow>;
      })}</TableBody></Table>
      <AlertDialog><AlertDialogTrigger asChild><Button disabled={decide.isPending}>Duyệt &amp; import</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Nạp dữ liệu theo mapping này?</AlertDialogTitle><AlertDialogDescription>Import chạy nền và chỉ ghi feedback đã sanitize. Analysis sẽ chưa tự chạy.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Kiểm tra lại</AlertDialogCancel><AlertDialogAction onClick={submit}>Xác nhận import</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    </section>
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
      <div><h3 className="font-heading text-base">5. Chọn cách phân tích</h3><p className="text-sm text-muted-foreground">Không tự chạy sau import. Mỗi run tối đa 100 feedback.</p></div>
      <ToggleGroup type="single" value={mode} onValueChange={(value) => { if (value) { setMode(value as "selected" | "batch"); preview.reset(); } }} variant="outline" className="justify-start">
        <ToggleGroupItem value="selected">Chọn từng mục</ToggleGroupItem><ToggleGroupItem value="batch">Chạy theo lô</ToggleGroupItem>
      </ToggleGroup>
      {mode === "selected" ? <div className="max-h-64 overflow-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead className="w-10" /><TableHead>Feedback chờ xử lý</TableHead></TableRow></TableHeader><TableBody>{rows.map((row) => <TableRow key={row.id}><TableCell><Checkbox checked={selected.has(row.id)} onCheckedChange={(checked) => { preview.reset(); setSelected((old) => { const next = new Set(old); if (checked) next.add(row.id); else next.delete(row.id); return next; }); }} /></TableCell><TableCell className="max-w-md"><span className="line-clamp-2">{row.feedback_text}</span></TableCell></TableRow>)}</TableBody></Table></div> : <Alert><Clock3 className="size-4" /><AlertTitle>Tối đa 100 / {feedbacks.data?.total ?? 0} pending</AlertTitle><AlertDescription>Chunk 10 feedback: một classify request và một embedding-array request mỗi chunk.</AlertDescription></Alert>}
      <Button variant="outline" onClick={requestPreview} disabled={preview.isPending || (mode === "selected" && selected.size === 0)}>{preview.isPending ? <Spinner data-icon="inline-start" /> : null}Tính cost receipt</Button>
      {preview.data ? <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted p-3 text-sm sm:grid-cols-3"><span><strong>{preview.data.selected_count}</strong><br />feedback</span><span><strong>{preview.data.logical_classify_requests}</strong><br />classify calls</span><span><strong>{preview.data.logical_embedding_requests}</strong><br />embed calls</span><span><strong>{preview.data.max_provider_attempts}</strong><br />attempts tối đa</span><span><strong>~{preview.data.estimated_input_tokens}</strong><br />input tokens</span><span><strong>{preview.data.remaining_count}</strong><br />còn lại</span></div> : null}
      {preview.data ? <AlertDialog><AlertDialogTrigger asChild><Button><Play data-icon="inline-start" />Xác nhận phân tích</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Chạy paid analysis theo receipt?</AlertDialogTitle><AlertDialogDescription>{preview.data.selected_count} feedback, {preview.data.logical_classify_requests + preview.data.logical_embedding_requests} logical calls, tối đa {preview.data.max_provider_attempts} provider attempts. Scope không đổi sẽ được claim atomically.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Quay lại</AlertDialogCancel><AlertDialogAction onClick={start}>Xác nhận chạy</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog> : null}
    </section>
  );
}

function ImportDetail({ id }: { id: string }) {
  const { openQueue } = useActivity();
  const detail = useImport(id);
  const item = detail.data;
  return <div className="mt-4 space-y-4"><Button variant="ghost" size="sm" onClick={openQueue}><ArrowLeft data-icon="inline-start" />Hàng chờ</Button>{detail.isPending ? <Spinner /> : null}{item ? <><div className="flex items-start justify-between gap-3"><div><h2 className="font-heading text-xl">{item.original_filename ?? "CSV import"}</h2><p className="text-sm text-muted-foreground">{item.id}</p></div>{statusBadge(item.status)}</div><ProfilePreview importId={id} /><MappingGate item={item} /><MappingReview item={item} />{item.status === "importing" ? <section className="space-y-2 rounded-xl border p-4"><h3 className="font-heading text-base">4. Import progress</h3><Progress value={35} /><p className="text-sm text-muted-foreground">Đang sanitize và ghi từng dòng. Có thể đóng Sheet.</p></section> : null}{item.status === "imported" ? <Alert><CheckCircle2 className="size-4" /><AlertTitle>Import hoàn tất</AlertTitle><AlertDescription>{item.report?.imported ?? item.row_count ?? 0} dòng đã nạp, {item.report?.failed ?? 0} lỗi. Analysis vẫn đang chờ xác nhận.</AlertDescription></Alert> : null}<AnalysisChooser item={item} /></> : <Alert variant="destructive"><AlertTitle>Không tải được import</AlertTitle><AlertDescription>{detail.error?.message}</AlertDescription></Alert>}</div>;
}

function RunDetail({ id }: { id: string }) {
  const { openQueue } = useActivity();
  const run = useRunProgress(id);
  const cancel = useCancelRun();
  const data = run.data;
  const pct = data?.total_count ? Math.round((data.processed_count / data.total_count) * 100) : 0;
  return <div className="mt-4 space-y-4"><Button variant="ghost" size="sm" onClick={openQueue}><ArrowLeft data-icon="inline-start" />Hàng chờ</Button>{data ? <><div className="flex items-center justify-between"><h2 className="font-heading text-xl">Analysis run</h2>{statusBadge(data.status)}</div><section className="space-y-3 rounded-xl border p-4"><Progress value={pct} /><p className="text-sm">{data.processed_count}/{data.total_count} hoàn tất · {data.failed_count} lỗi</p><p className="text-xs text-muted-foreground">Mode {data.mode} · chunk {data.chunk_size}. Dừng có hiệu lực sau {data.mode === "batch" ? "chunk" : "item"} hiện tại.</p><div className="flex flex-wrap gap-2">{data.status === "running" ? <Button variant="outline" disabled={cancel.isPending || Boolean(data.cancel_requested_at)} onClick={() => cancel.mutate(id)}><Ban data-icon="inline-start" />{data.cancel_requested_at ? "Đang chờ dừng" : "Dừng run"}</Button> : null}<Button variant="outline" asChild><Link href={`/analysis?run=${id}`}>Xem kết quả chi tiết</Link></Button></div>{data.error ? <Alert variant="destructive"><TriangleAlert className="size-4" /><AlertTitle>Có lỗi</AlertTitle><AlertDescription>{data.error}</AlertDescription></Alert> : null}</section></> : <Spinner />}</div>;
}

export function ActivitySheet() {
  const activity = useActivity();
  const param = activity.activityParam;
  const detail = param?.startsWith("import:") ? <ImportDetail id={param.slice(7)} /> : param?.startsWith("run:") ? <RunDetail id={param.slice(4)} /> : <ActivityQueue />;
  return (
    <Sheet open={Boolean(param)} onOpenChange={(open) => { if (!open) activity.closeActivity(); }}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-3xl">
        <SheetHeader><SheetTitle>Activity Center</SheetTitle><SheetDescription>Review, import và chạy AI có budget guard — không rời trang hiện tại.</SheetDescription></SheetHeader>
        <div className="px-4 pb-6">{detail}</div>
      </SheetContent>
    </Sheet>
  );
}

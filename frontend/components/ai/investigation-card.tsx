"use client";
import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, BookOpenText, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { useAgentDecision, useAgentRun } from "@/hooks/use-agent";
import { apiFetch } from "@/lib/api";
import { TOOL_LABELS, formatElapsed, isSlowInvestigation } from "@/lib/investigation";
import { EvidenceCard } from "./evidence-card";
import { agentItemText, dedupeEvidence, humanizeAgentText, parseEvidence } from "@/lib/evidence";
import { RUN_STATUS_TONE } from "@/lib/tone";
import type { AgentDecision, InsightsListResponse, PendingApproval } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AiTrace } from "./ai-trace";
import { ConfidenceMeter } from "./confidence-meter";
import { InvestigationActions } from "./investigation-actions";

const STATUS: Record<string, string> = {
  running: "Đang điều tra", pending_approval: "Chờ bạn duyệt",
  decision_processing: "Đang lưu quyết định", completed: "Đã hoàn tất",
  failed: "Chưa hoàn tất", cancelled: "Đã dừng",
};

/**
 * Khung quyết định đặt CẠNH kết luận (mẫu "duyệt bên cạnh nội dung"): bốn lựa
 * chọn luôn nằm trong tầm mắt khi đọc bản nháp, không phải cuộn xuống cuối thẻ.
 */
export function FindingReview({ pending, busy, onSubmit }: {
  pending: PendingApproval; busy: boolean;
  onSubmit: (action: AgentDecision, edit?: {title: string; finding: string}, reason?: string) => void;
}) {
  const id = useId();
  const [mode, setMode] = useState<"edit" | "reject" | "investigate_more" | null>(null);
  const [title, setTitle] = useState(pending.insight.title);
  const [finding, setFinding] = useState(pending.insight.finding);
  const [reason, setReason] = useState("");
  return (
    <section aria-labelledby={`${id}-heading`} className="flex flex-col gap-3 rounded-lg border border-sun-line bg-sun-soft/40 p-4">
      <div className="flex flex-col gap-1">
        <p id={`${id}-heading`} className="text-sm font-medium">Bạn quyết định kết luận này</p>
        <p className="text-xs text-muted-foreground">Duyệt để lưu vào Báo cáo. Mọi quyết định đều được ghi lại.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => onSubmit("approve")}>Duyệt kết luận</Button>
        <Button size="sm" variant={mode === "edit" ? "secondary" : "outline"} disabled={busy} aria-pressed={mode === "edit"} onClick={() => setMode("edit")}>Chỉnh sửa</Button>
        <Button size="sm" variant={mode === "investigate_more" ? "secondary" : "outline"} disabled={busy} aria-pressed={mode === "investigate_more"} onClick={() => setMode("investigate_more")}>Điều tra thêm</Button>
        <Button size="sm" variant="ghost" disabled={busy} aria-pressed={mode === "reject"} onClick={() => setMode("reject")}>Từ chối</Button>
      </div>
      {busy ? <p role="status" className="flex items-center gap-2 text-sm"><Spinner />Đang xử lý. Kết quả sẽ cập nhật ngay tại đây.</p> : null}
      {mode ? (
        <FieldGroup>
          {mode === "edit" ? <>
            <Field><FieldLabel htmlFor={`${id}-title`}>Tiêu đề</FieldLabel><Input id={`${id}-title`} value={title} disabled={busy} onChange={e => setTitle(e.target.value)} /></Field>
            <Field><FieldLabel htmlFor={`${id}-finding`}>Kết luận</FieldLabel><Textarea id={`${id}-finding`} rows={5} value={finding} disabled={busy} onChange={e => setFinding(e.target.value)} /></Field>
          </> : null}
          <Field>
            <FieldLabel htmlFor={`${id}-reason`}>{mode === "investigate_more" ? "Bạn muốn kiểm tra thêm điều gì?" : "Lý do (không bắt buộc)"}</FieldLabel>
            <Textarea id={`${id}-reason`} rows={2} maxLength={1000} value={reason} disabled={busy} onChange={e => setReason(e.target.value)} />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={busy || (mode === "edit" && (!title.trim() || !finding.trim())) || (mode === "investigate_more" && reason.trim().length < 3)}
              onClick={() => onSubmit(mode, mode === "edit" ? {title: title.trim(), finding: finding.trim()} : undefined, reason.trim() || undefined)}>
              {mode === "edit" ? "Lưu sửa và duyệt" : mode === "reject" ? "Xác nhận từ chối" : "Tiếp tục điều tra"}
            </Button>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => setMode(null)}>Huỷ</Button>
          </div>
        </FieldGroup>
      ) : null}
    </section>
  );
}

/** Đồng hồ + bước hiện tại ngay trên thẻ (không giấu trong "Hoạt động"):
 * người dùng phân biệt được "đang chạy" với "treo", và biết phải làm gì khi
 * cuộc điều tra lâu hơn thường lệ (QA HN-016). */
function RunningProgress({startedAt, step, collected, onRetry, onOpenActivity}: {
  startedAt?: string | null; step: string; collected: number; onRetry?: () => void; onOpenActivity: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const slow = isSlowInvestigation(startedAt, now);
  return <div className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-3 text-sm" role="status">
    <div className="flex flex-wrap items-center gap-2">
      <Spinner />
      <p className="font-medium">{step}…</p>
      {startedAt ? <span className="font-mono text-xs text-muted-foreground">đã chạy {formatElapsed(startedAt, now)}</span> : null}
      <Button size="sm" variant="ghost" className="ml-auto" onClick={onOpenActivity}>Xem từng bước</Button>
    </div>
    <p className="text-xs text-muted-foreground">
      {collected > 0 ? `Đã thu thập ${collected} kết quả. ` : "AI đang lập kế hoạch — bước đầu thường mất 20–60 giây. "}
      Thông thường mất 1–3 phút. Khi đủ bằng chứng, bản nháp sẽ xuất hiện tại đây để bạn duyệt. Bạn có thể rời trang rồi quay lại.
    </p>
    {slow ? <Alert>
      <AlertTitle>Lâu hơn thường lệ</AlertTitle>
      <AlertDescription className="flex flex-col gap-3">
        <span>Cuộc điều tra vẫn đang chạy và chưa báo lỗi. Bạn có thể đợi thêm, hoặc hỏi lại câu này — phiên cũ vẫn được giữ trong lịch sử.</span>
        {onRetry ? <div><Button size="sm" variant="outline" onClick={onRetry}>Hỏi lại câu này</Button></div> : null}
      </AlertDescription>
    </Alert> : null}
  </div>;
}

/** Nhãn ngắn cho chip trích dẫn: loại bước kiểm tra, rơi về tiêu đề rút gọn. */
function citationLabel(statement: string): string {
  const view = parseEvidence(statement);
  const label = view.kind || view.title || "Bằng chứng";
  return label.length > 28 ? `${label.slice(0, 27)}…` : label;
}

export function InvestigationCard({runId, question, onRetry}: {
  runId: string; question?: string | null; onRetry?: () => void;
}) {
  const run = useAgentRun(runId);
  const decision = useAgentDecision();
  const data = run.data;
  const pending = data?.pending_approval;
  const running = data?.status === "running";
  const processing = decision.isPending || data?.status === "decision_processing";
  const reports = useQuery({
    queryKey: ["insights", "investigation", runId],
    queryFn: () => apiFetch<InsightsListResponse>("/api/insights"),
    enabled: data?.status === "completed", staleTime: 0,
  });
  const report = reports.data?.items.find(item => item.run_id === runId);
  const draft = pending?.insight;
  const evidence = dedupeEvidence(pending?.evidence ?? report?.evidence ?? []);
  const findingConfidence = draft?.finding_confidence ?? report?.finding_confidence;
  const limitations = draft?.limitations ?? report?.limitations ?? [];
  const hypothesis = draft?.hypothesis_statement ?? report?.hypothesis?.statement;
  const reviewing = Boolean(pending && !running);

  const uid = useId();
  const [panel, setPanel] = useState<"sources" | "activity" | null>(null);
  const [focusSource, setFocusSource] = useState<number | null>(null);
  const [showLimits, setShowLimits] = useState(false);

  const openSource = (index: number | null) => {
    setFocusSource(index);
    setPanel("sources");
  };
  // Mở bảng Nguồn ở đúng trích dẫn người dùng vừa bấm.
  useEffect(() => {
    if (panel !== "sources" || focusSource == null) return;
    const frame = requestAnimationFrame(() => {
      document.getElementById(`${uid}-src-${focusSource}`)?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
    return () => cancelAnimationFrame(frame);
  }, [panel, focusSource, uid]);

  const evidencePreview = evidence.length ? (
    <section aria-label="Bằng chứng nổi bật" className="flex min-w-0 flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-medium">Bằng chứng nổi bật</h4>
        <Button size="sm" variant="ghost" onClick={() => openSource(null)}>Tất cả {evidence.length} nguồn</Button>
      </div>
      {evidence.slice(0, 2).map(({ item, repeats }, i) => (
        <EvidenceCard key={item.evidence_id ?? i} statement={item.statement} index={i + 1} repeats={repeats} compact />
      ))}
    </section>
  ) : <p className="text-sm text-muted-foreground">Chưa có bằng chứng để xác nhận kết luận này.</p>;

  return <Card className="@container w-full min-w-0">
    <CardHeader>
      <p className="text-xs text-muted-foreground">Câu hỏi điều tra</p>
      <CardTitle className="text-base">{question || pending?.question || report?.title || "Điều tra phản hồi"}</CardTitle>
      <CardDescription className="flex flex-wrap items-center gap-2" aria-live="polite">
        {(processing || run.isPending) && !running ? <Spinner /> : null}
        <Badge variant={data ? RUN_STATUS_TONE[data.status] ?? "secondary" : "secondary"}>{data ? STATUS[data.status] ?? "Đang cập nhật" : "Đang kết nối"}</Badge>
        {data?.progress ? <span>{data.progress.evidence_count} kết quả đã thu thập</span> : null}
      </CardDescription>
      <CardAction className="flex gap-1">
        <Button size="sm" variant="ghost" onClick={() => setPanel("activity")} aria-haspopup="dialog">
          <Activity data-icon="inline-start" />Hoạt động
        </Button>
        <Button size="sm" variant="ghost" disabled={!evidence.length} onClick={() => openSource(null)} aria-haspopup="dialog">
          <BookOpenText data-icon="inline-start" />Nguồn{evidence.length ? ` (${evidence.length})` : ""}
        </Button>
      </CardAction>
    </CardHeader>
    <CardContent className="flex flex-col gap-4">
      {run.isError ? <Alert variant="destructive"><AlertTitle>Chưa đọc được trạng thái</AlertTitle><AlertDescription>Phiên vẫn được giữ. Bạn có thể kết nối lại.</AlertDescription><Button size="sm" variant="outline" onClick={() => void run.refetch()}>Kết nối lại</Button></Alert> : null}
      {running ? <RunningProgress
        startedAt={data.started_at}
        step={data.progress?.last_tool ? TOOL_LABELS[data.progress.last_tool] ?? "Đối chiếu dữ liệu" : "Đang xác định dữ liệu cần kiểm tra"}
        collected={data.progress?.evidence_count ?? 0}
        onRetry={onRetry}
        onOpenActivity={() => setPanel("activity")}
      /> : null}
      {draft || report ? <div className="grid min-w-0 items-start gap-5 @min-[44rem]:grid-cols-[minmax(0,1fr)_minmax(16rem,0.8fr)]">
        <article className="flex min-w-0 flex-col gap-3">
          <h3 className="font-heading text-xl leading-snug">{draft?.title ?? report?.title}</h3>
          {findingConfidence != null ? <ConfidenceMeter value={findingConfidence} /> : null}
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{humanizeAgentText(draft?.finding ?? report?.finding ?? "")}</p>
          {evidence.length ? <div className="flex flex-wrap items-center gap-1.5" aria-label="Kết luận dựa trên">
            <span className="text-xs text-muted-foreground">Dựa trên</span>
            {evidence.slice(0, 6).map(({ item }, i) => (
              <button
                key={item.evidence_id ?? i}
                type="button"
                onClick={() => openSource(i)}
                className="inline-flex max-w-full items-center gap-1 rounded-full border border-sky-line bg-sky-soft/50 px-2 py-0.5 text-xs text-sky-ink transition-colors hover:bg-sky-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <span className="font-mono">{i + 1}</span>
                <span className="truncate">{citationLabel(item.statement)}</span>
              </button>
            ))}
            {evidence.length > 6 ? <Button size="xs" variant="ghost" onClick={() => openSource(6)}>+{evidence.length - 6}</Button> : null}
          </div> : null}
          {hypothesis ? <p className="border-l-2 border-sun-line pl-3 text-sm text-muted-foreground">Giả thuyết cần kiểm chứng: {humanizeAgentText(hypothesis)}</p> : null}
          {limitations.length ? <div className="flex flex-col gap-2">
            <Button size="sm" variant="ghost" className="self-start" aria-expanded={showLimits} onClick={() => setShowLimits(!showLimits)}>
              <ChevronDown data-icon="inline-start" className={cn("transition-transform", showLimits && "rotate-180")} />
              Giới hạn của kết luận ({limitations.length})
            </Button>
            {showLimits ? <ul className="flex list-disc flex-col gap-1 pl-5 text-xs text-muted-foreground">{limitations.map((text, i) => <li key={i}>{agentItemText(text)}</li>)}</ul> : null}
          </div> : null}
          {reviewing ? evidencePreview : null}
        </article>
        <aside className="flex min-w-0 flex-col gap-3 @min-[44rem]:sticky @min-[44rem]:top-20">
          {reviewing && pending ? <FindingReview key={pending.insight_id ?? runId} pending={pending} busy={processing} onSubmit={(action, editedInsight, reason) => {
            decision.mutate({runId, action, editedInsight, reason}, {
              onSuccess: () => toast.info(action === "investigate_more" ? "Đã nhận yêu cầu điều tra thêm." : "Đã nhận quyết định, đang lưu…"),
              onError: () => toast.error("Chưa gửi được quyết định. Nội dung bạn nhập vẫn được giữ."),
            });
          }} /> : evidencePreview}
        </aside>
      </div> : null}
      {data?.error ? <Alert variant="destructive"><AlertTitle>{data.status === "failed" ? "Điều tra chưa hoàn tất" : "Chưa lưu được quyết định"}</AlertTitle><AlertDescription>Phiên và dữ liệu vẫn được giữ. Hãy kiểm tra kết nối rồi thử lại.</AlertDescription></Alert> : null}
      {!reviewing && processing ? <p role="status" className="flex items-center gap-2 text-sm"><Spinner />Đang lưu quyết định…</p> : null}
      {data?.status === "completed" ? <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-muted/30 px-3 py-2">
        <p className="text-sm">{report?.status === "rejected" ? "Bạn đã từ chối kết luận. Lịch sử được giữ lại." : "Quyết định đã được lưu. Phiên điều tra đã hoàn tất."}</p>
        <Button size="sm" variant="outline" asChild><Link href={report ? `/reports?report=${report.id}` : "/reports"}>Xem báo cáo</Link></Button>
      </div> : null}
      {report && (report.status === "approved" || report.status === "edited") ? <InvestigationActions insightId={report.id} /> : null}
      {data?.status === "failed" && onRetry ? <Button size="sm" variant="outline" className="self-start" onClick={onRetry}>Thử lại câu hỏi này</Button> : null}
    </CardContent>

    <Sheet open={panel != null} onOpenChange={(open) => !open && setPanel(null)}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {panel === "sources" ? <>
          <SheetHeader>
            <SheetTitle>Nguồn của kết luận</SheetTitle>
            <SheetDescription>{evidence.length} bằng chứng AI đã thu thập. Số thứ tự khớp với chip trích dẫn trong kết luận.</SheetDescription>
          </SheetHeader>
          <ol className="flex flex-col gap-3 px-4 pb-6">
            {evidence.map(({ item, repeats }, i) => (
              <li key={item.evidence_id ?? i} id={`${uid}-src-${i}`} className="scroll-mt-4">
                <EvidenceCard
                  statement={item.statement}
                  index={i + 1}
                  repeats={repeats}
                  className={cn(focusSource === i && "border-sky-line ring-2 ring-sky-soft")}
                />
              </li>
            ))}
          </ol>
        </> : <>
          <SheetHeader>
            <SheetTitle>Hoạt động của AI</SheetTitle>
            <SheetDescription>Từng bước AI đã chạy trong cuộc điều tra này. Chỉ hiện số liệu kỹ thuật, không hiện nội dung phản hồi.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-3 px-4 pb-6">
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-xs">
              <dt className="text-muted-foreground">Trạng thái</dt><dd>{data ? STATUS[data.status] ?? data.status : "Đang kết nối"}</dd>
              <dt className="text-muted-foreground">Mã phiên</dt><dd className="break-all font-mono">{runId}</dd>
            </dl>
            {data?.error ? <p className="break-words text-xs text-destructive">{data.error}</p> : null}
            <AiTrace runId={runId} active={running} startedAt={data?.started_at} />
          </div>
        </>}
      </SheetContent>
    </Sheet>
  </Card>;
}

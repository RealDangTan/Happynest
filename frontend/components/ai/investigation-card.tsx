"use client";
import { useId, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { useAgentDecision, useAgentRun } from "@/hooks/use-agent";
import { apiFetch } from "@/lib/api";
import { readableEvidence, TOOL_LABELS } from "@/lib/investigation";
import { cn } from "@/lib/utils";
import type { AgentDecision, InsightsListResponse, PendingApproval } from "@/lib/types";
import { AiTrace } from "./ai-trace";
import { InvestigationActions } from "./investigation-actions";

const STATUS: Record<string, string> = {
  running: "Đang điều tra", pending_approval: "Chờ bạn duyệt",
  decision_processing: "Đang lưu quyết định", completed: "Đã hoàn tất",
  failed: "Chưa hoàn tất", cancelled: "Đã dừng",
};

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
    <div className="flex flex-col gap-3 border-t pt-4">
      <p className="text-sm font-medium">Bạn quyết định kết luận này</p>
      <p className="text-xs text-muted-foreground">Duyệt để lưu vào Báo cáo. Mọi quyết định đều được ghi lại.</p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => onSubmit("approve")}>Duyệt kết luận</Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => setMode("edit")}>Chỉnh sửa</Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => setMode("investigate_more")}>Điều tra thêm</Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => setMode("reject")}>Từ chối</Button>
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
    </div>
  );
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
  const evidence = pending?.evidence ?? report?.evidence ?? [];
  const [showEvidence, setShowEvidence] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  return <Card className="min-w-0 w-full">
    <CardHeader>
      <CardTitle className="text-base">{question || pending?.question || report?.title || "Điều tra phản hồi"}</CardTitle>
      <CardDescription className="flex flex-wrap items-center gap-2" aria-live="polite">
        {(running || processing || run.isPending) ? <Spinner /> : null}
        <Badge variant={data?.status === "failed" ? "destructive" : "secondary"}>{data ? STATUS[data.status] ?? "Đang cập nhật" : "Đang kết nối"}</Badge>
        {data?.progress ? <span>{data.progress.evidence_count} kết quả đã thu thập</span> : null}
      </CardDescription>
    </CardHeader>
    <CardContent className="flex flex-col gap-4">
      {run.isError ? <Alert variant="destructive"><AlertTitle>Chưa đọc được trạng thái</AlertTitle><AlertDescription>Phiên vẫn được giữ. Bạn có thể kết nối lại.</AlertDescription><Button size="sm" variant="outline" onClick={() => void run.refetch()}>Kết nối lại</Button></Alert> : null}
      {running ? <div className="flex flex-col gap-2 text-sm">
        <p>{data.progress?.last_tool ? TOOL_LABELS[data.progress.last_tool] ?? "Đối chiếu dữ liệu" : "Đang xác định dữ liệu cần kiểm tra"}…</p>
        <p className="text-xs text-muted-foreground">Khi đủ bằng chứng, bản nháp sẽ xuất hiện tại đây để bạn duyệt. Bạn có thể rời trang rồi quay lại.</p>
      </div> : null}
      {draft || report ? <>
        <h3 className="font-heading text-lg leading-snug">{draft?.title ?? report?.title}</h3>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{draft?.finding ?? report?.finding}</p>
        <p className="text-xs text-muted-foreground">Độ tin cậy ước lượng: {Math.round((draft?.finding_confidence ?? report?.finding_confidence ?? 0) * 100)}%</p>
        {draft?.hypothesis_statement || report?.hypothesis?.statement ? <p className="border-l-2 pl-3 text-sm text-muted-foreground">Giả thuyết cần kiểm chứng: {draft?.hypothesis_statement ?? report?.hypothesis?.statement}</p> : null}
        {(draft?.limitations ?? report?.limitations ?? []).length ? <ul className="flex list-disc flex-col gap-1 pl-5 text-xs text-muted-foreground">{(draft?.limitations ?? report?.limitations ?? []).map((text, i) => <li key={i}>{String(text)}</li>)}</ul> : null}
        {evidence.length ? <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Bằng chứng ({evidence.length})</p>
          {(showEvidence ? evidence : evidence.slice(0, 2)).map((item, i) => <p key={item.evidence_id ?? i} className={cn("rounded-md border p-3 text-sm leading-relaxed break-words", !showEvidence && "line-clamp-4")}>{readableEvidence(item.statement)}</p>)}
          {evidence.length > 2 || evidence.some(item => item.statement.length > 400) ? <Button size="sm" variant="ghost" onClick={() => setShowEvidence(!showEvidence)}>{showEvidence ? "Thu gọn bằng chứng" : "Xem toàn bộ bằng chứng"}</Button> : null}
        </div> : <p className="text-sm text-muted-foreground">Chưa có bằng chứng để xác nhận kết luận này.</p>}
      </> : null}
      {data?.error ? <Alert variant="destructive"><AlertTitle>{data.status === "failed" ? "Điều tra chưa hoàn tất" : "Chưa lưu được quyết định"}</AlertTitle><AlertDescription>Phiên và dữ liệu vẫn được giữ. Hãy kiểm tra kết nối rồi thử lại.</AlertDescription></Alert> : null}
      {pending && !running ? <FindingReview key={pending.insight_id ?? runId} pending={pending} busy={processing} onSubmit={(action, editedInsight, reason) => {
        decision.mutate({runId, action, editedInsight, reason}, {
          onSuccess: () => toast.info(action === "investigate_more" ? "Đã nhận yêu cầu điều tra thêm." : "Đã nhận quyết định, đang lưu…"),
          onError: () => toast.error("Chưa gửi được quyết định. Nội dung bạn nhập vẫn được giữ."),
        });
      }} /> : processing ? <p role="status" className="text-sm">Đang lưu quyết định…</p> : null}
      {data?.status === "completed" ? <div className="flex flex-col gap-2">
        <p className="text-sm">{report?.status === "rejected" ? "Bạn đã từ chối kết luận. Lịch sử được giữ lại." : "Quyết định đã được lưu. Phiên điều tra đã hoàn tất."}</p>
        <Button size="sm" variant="outline" asChild><Link href={report ? `/reports?report=${report.id}` : "/reports"}>Xem báo cáo</Link></Button>
      </div> : null}
      {report && (report.status === "approved" || report.status === "edited") ? <InvestigationActions insightId={report.id} /> : null}
      {data?.status === "failed" && onRetry ? <Button size="sm" variant="outline" onClick={onRetry}>Thử lại câu hỏi này</Button> : null}
      <div className="border-t pt-2">
        <Button size="sm" variant="ghost" onClick={() => setShowDiagnostics(!showDiagnostics)} aria-expanded={showDiagnostics}>{showDiagnostics ? "Ẩn chi tiết kỹ thuật" : "Chi tiết kỹ thuật"}</Button>
        {showDiagnostics ? <div className="flex flex-col gap-2 pt-2">
          <p className="break-all font-mono text-xs text-muted-foreground">{runId}</p>
          {data?.error ? <p className="break-words text-xs">{data.error}</p> : null}
          <AiTrace runId={runId} active={running} startedAt={data?.started_at} />
        </div> : null}
      </div>
    </CardContent>
  </Card>;
}

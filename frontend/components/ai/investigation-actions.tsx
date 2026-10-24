"use client";
import { useId, useState } from "react";
import { toast } from "sonner";
import { useActions, useGenerateActions, useUpdateAction } from "@/hooks/use-actions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { ActionDecisionSupport } from "@/components/actions/action-decision-support";
import { effectiveScores } from "@/lib/matrix";
import type { ActionItem } from "@/lib/types";

const TEAMS: Record<string, string> = { MARKETING:"Tiếp thị", LEGAL:"Pháp chế", DESIGN:"Thiết kế", FINANCE:"Tài chính", ENGINEERING:"Kỹ thuật", OPERATION:"Vận hành", SALES:"Kinh doanh", SUPPORT:"Hỗ trợ" };

function ReviewAction({action}: {action: ActionItem}) {
  const id = useId();
  const update = useUpdateAction();
  const [editing, setEditing] = useState(false);
  const [analysis, setAnalysis] = useState(false);
  const [text, setText] = useState(action.recommendation);
  const [scores, setScores] = useState(effectiveScores(action));
  const [reason, setReason] = useState("");
  const decided = action.status === "accepted" || action.status === "rejected";
  const send = (status: "accepted" | "rejected") => update.mutate({actionId: action.id, body: {
    status, ...(editing && status === "accepted" ? {recommendation: text, ...scores, override_reason: reason} : {}),
  }}, {onSuccess: () => { setEditing(false); toast.success("Đã lưu quyết định hành động."); }, onError: () => toast.error("Chưa lưu được. Nội dung chỉnh sửa vẫn được giữ.")});
  return <div className="flex flex-col gap-3 rounded-lg border p-3">
    <div className="flex flex-wrap items-center gap-2"><Badge variant="outline">{TEAMS[action.function] ?? "Nhóm phụ trách"}</Badge><span className="text-xs text-muted-foreground">Ưu tiên {action.priority_score.toFixed(1)}</span>{decided ? <Badge variant="secondary">{action.status === "accepted" ? "Đã nhận" : "Đã từ chối"}</Badge> : null}</div>
    <p className="text-sm font-medium">{action.recommendation}</p>
    <p className="text-xs text-muted-foreground">{action.rationale}</p>
    {editing ? <FieldGroup>
      <Field><FieldLabel htmlFor={`${id}-text`}>Hành động</FieldLabel><Textarea id={`${id}-text`} value={text} onChange={e => setText(e.target.value)} disabled={update.isPending} /></Field>
      <div className="flex flex-wrap gap-3">{([["impact","Tác động"],["effort","Công sức"],["urgency","Khẩn cấp"]] as const).map(([key,label]) => <Field key={key} className="w-24"><FieldLabel htmlFor={`${id}-${key}`}>{label} (1–10)</FieldLabel><Input id={`${id}-${key}`} type="number" min={1} max={10} value={scores[key]} disabled={update.isPending} onChange={e => {const n=Number(e.target.value); if(Number.isInteger(n)&&n>=1&&n<=10) setScores({...scores,[key]:n});}} /></Field>)}</div>
      <Field><FieldLabel htmlFor={`${id}-reason`}>Lý do chỉnh sửa</FieldLabel><Textarea id={`${id}-reason`} rows={2} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)} disabled={update.isPending} /></Field>
    </FieldGroup> : null}
    {!decided ? <div className="flex flex-wrap gap-2">
      <Button size="sm" disabled={update.isPending || text.trim().length < 3} onClick={() => send("accepted")}>{update.isPending ? <Spinner data-icon="inline-start" /> : null}{editing ? "Lưu sửa và nhận" : "Nhận hành động"}</Button>
      <Button size="sm" variant="outline" disabled={update.isPending} onClick={() => setEditing(!editing)}>{editing ? "Huỷ sửa" : "Chỉnh điểm / nội dung"}</Button>
      <Button size="sm" variant="ghost" disabled={update.isPending} onClick={() => send("rejected")}>Từ chối</Button>
    </div> : null}
    <Button size="sm" variant="ghost" onClick={() => setAnalysis(!analysis)} aria-expanded={analysis}>{analysis ? "Ẩn phân tích đề xuất" : "Vì sao đề xuất hành động này?"}</Button>
    {analysis ? <ActionDecisionSupport action={action} /> : null}
  </div>;
}

export function InvestigationActions({insightId}: {insightId: string}) {
  const actions = useActions(insightId);
  const generate = useGenerateActions();
  const [error, setError] = useState(false);
  return <section className="flex flex-col gap-3 border-t pt-4">
    <h3 className="text-sm font-medium">Bước tiếp theo: gợi ý hành động</h3>
    <p className="text-xs text-muted-foreground">Bạn có thể nhận, chỉnh sửa hoặc từ chối từng gợi ý ngay trong cuộc trò chuyện.</p>
    {actions.isError ? <Button size="sm" variant="outline" onClick={() => void actions.refetch()}>Tải lại gợi ý</Button> : null}
    {(actions.data?.items ?? []).map(action => <ReviewAction key={action.id} action={action} />)}
    {!actions.isPending && !actions.isError && !actions.data?.items.length ? <Button size="sm" variant="outline" disabled={generate.isPending} onClick={() => {setError(false); generate.mutate(insightId, {onSuccess: result => {setError(Boolean(result.generation_error)); if (!result.generation_error && !result.actions_created) toast.info("Chưa có gợi ý phù hợp từ bằng chứng hiện tại.");}, onError: () => setError(true)});}}>{generate.isPending ? <Spinner data-icon="inline-start" /> : null}{generate.isPending ? "Đang tạo gợi ý…" : "Tạo gợi ý hành động bằng AI"}</Button> : null}
    {error ? <p role="alert" className="text-sm text-destructive">Chưa tạo được gợi ý. Bạn có thể thử lại; kết luận đã duyệt vẫn được giữ.</p> : null}
  </section>;
}

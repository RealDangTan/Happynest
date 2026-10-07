"use client";
import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CircleCheck,
  FileText,
  Pencil,
  Search,
  Sparkles,
  Trash2,
  X,
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
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AiBadge } from "@/components/ai/ai-badge";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useInsights, useDeleteInsight, useUpdateInsight } from "@/hooks/use-insights";
import { useAgentDecision, useAgentRun } from "@/hooks/use-agent";
import { useGenerateActions } from "@/hooks/use-actions";
import { useMe } from "@/hooks/use-me";
import { useProduct } from "@/hooks/use-product";
import type { InsightItem } from "@/lib/types";

const STATUS_TONE: Record<
  string,
  { label: string; tone: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending: { label: "Needs review", tone: "default" },
  investigating: { label: "Investigating", tone: "secondary" },
  approved: { label: "Approved", tone: "outline" },
  edited: { label: "Approved (edited)", tone: "outline" },
  rejected: { label: "Rejected", tone: "destructive" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_TONE[status] ?? { label: status, tone: "secondary" as const };
  return <Badge variant={s.tone}>{s.label}</Badge>;
}

function EvidenceChip({ id }: { id: string }) {
  return (
    <span className="rounded bg-signal/10 px-1.5 py-0.5 font-mono text-xs text-signal">
      E-{id.slice(0, 4)}
    </span>
  );
}

// ------------------------------------------------------------------ Report body

function ReportBody({
  title,
  status,
  finding,
  findingConfidence,
  hypothesis,
  impact,
  limitations,
  evidence,
  runId,
}: {
  title: string;
  status: string;
  finding: string;
  findingConfidence: number | null;
  hypothesis: { statement: string | null; confidence: number | null } | null;
  impact: string[];
  limitations: string[];
  evidence: { evidence_id: string; statement: string; source_tool?: string }[];
  runId: string | null;
}) {
  return (
    <article className="space-y-6">
      <header className="space-y-1">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-heading text-2xl leading-snug">{title}</h2>
          <StatusBadge status={status} />
        </div>
        {runId ? (
          <p className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
            Investigation {runId.slice(0, 8)}
            <AiBadge />
          </p>
        ) : null}
      </header>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Finding
        </h3>
        <p className="font-heading text-lg leading-relaxed">{finding}</p>
        {findingConfidence != null ? (
          <p className="font-mono text-xs text-muted-foreground">
            Confidence {findingConfidence.toFixed(2)}
          </p>
        ) : null}
      </section>

      {hypothesis?.statement ? (
        <section className="space-y-2 border-l-2 border-pollen pl-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-warning">
            Hypothesis — unconfirmed
          </h3>
          <p className="text-sm leading-relaxed">{hypothesis.statement}</p>
          {hypothesis.confidence != null ? (
            <p className="font-mono text-xs text-muted-foreground">
              Confidence {hypothesis.confidence.toFixed(2)}
            </p>
          ) : null}
        </section>
      ) : null}

      {impact.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Impact
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {impact.map((i, idx) => (
              <li key={idx}>{typeof i === "string" ? i : JSON.stringify(i)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {limitations.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Limitations
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {limitations.map((l, idx) => (
              <li key={idx}>{typeof l === "string" ? l : JSON.stringify(l)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Evidence
        </h3>
        {evidence.length ? (
          <ul className="space-y-2">
            {evidence.map((e) => (
              <li
                key={e.evidence_id}
                className="rounded-lg border bg-secondary/30 p-3 text-sm"
              >
                <div className="flex items-center gap-2">
                  <EvidenceChip id={e.evidence_id} />
                  <span className="font-mono text-xs text-muted-foreground">
                    {e.source_tool}
                  </span>
                </div>
                <p className="mt-1 break-words">{e.statement}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No evidence recorded.</p>
        )}
      </section>
    </article>
  );
}

// ------------------------------------------------------------------ G2 bar

function GateTwoBar({
  runId,
  onDecided,
}: {
  runId: string;
  onDecided: (insightIds: string[]) => void;
}) {
  const decision = useAgentDecision();
  const [editOpen, setEditOpen] = useState(false);
  const [editedTitle, setEditedTitle] = useState("");
  const [editedFinding, setEditedFinding] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const send = (
    action: "approve" | "edit" | "investigate_more" | "reject",
    payload?: {
      editedInsight?: { title?: string; finding?: string };
      reason?: string;
    },
  ) => {
    decision.mutate(
      { runId, action, ...payload },
      {
        onSuccess: (res) => {
          if (action === "approve") toast.success("Finding approved.");
          if (action === "edit") toast.success("Edit saved and approved.");
          if (action === "reject")
            toast.success("Finding rejected — retained in history.");
          if (action === "investigate_more") toast.success("Back to investigation.");
          onDecided(res.insights_created ?? []);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Decision failed"),
      },
    );
  };

  return (
    <div className="rounded-xl border-2 border-pollen/60 bg-card p-4">
      <p className="text-sm font-semibold">G2 — Review the finding</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Your decision is recorded with time, reviewer, and revision.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="outline" disabled={decision.isPending} onClick={() => setRejectOpen(true)}>
          <X data-icon="inline-start" />
          Reject
        </Button>
        <Button
          variant="outline"
          disabled={decision.isPending}
          onClick={() => send("investigate_more")}
        >
          <Search data-icon="inline-start" />
          Investigate more
        </Button>
        <Button variant="outline" disabled={decision.isPending} onClick={() => setEditOpen(true)}>
          <Pencil data-icon="inline-start" />
          Edit finding
        </Button>
        <Button disabled={decision.isPending} onClick={() => send("approve")}>
          <CircleCheck data-icon="inline-start" />
          Approve finding
        </Button>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit finding</DialogTitle>
            <DialogDescription>
              Evidence stays as recorded — your edit is applied on top of it.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              placeholder="Title"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
            />
            <Textarea
              placeholder="Finding"
              rows={4}
              value={editedFinding}
              onChange={(e) => setEditedFinding(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Keep as is
            </Button>
            <Button
              onClick={() => {
                send("edit", {
                  editedInsight: {
                    ...(editedTitle ? { title: editedTitle } : {}),
                    ...(editedFinding ? { finding: editedFinding } : {}),
                  },
                });
                setEditOpen(false);
              }}
            >
              Save edit and approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject this finding?</AlertDialogTitle>
            <AlertDialogDescription>
              Rejected reports remain visible in history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea
            placeholder="Reason (optional)"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                send("reject", { reason: rejectReason || undefined });
                setRejectOpen(false);
              }}
            >
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ------------------------------------------------------------------ Screen

function ReportEditDialog({
  report,
  open,
  onOpenChange,
}: {
  report: InsightItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const update = useUpdateInsight();
  // State khởi tạo từ prop; mount site dùng key={report.id} để re-seed form
  // mỗi lần mở report khác — không cần effect ghi đè state.
  const [title, setTitle] = useState(report?.title ?? "");
  const [finding, setFinding] = useState(report?.finding ?? "");

  if (!report) return null;

  const save = () => {
    const body: { title?: string; finding?: string } = {};
    if (title.trim() && title !== report.title) body.title = title.trim();
    if (finding.trim() && finding !== report.finding) body.finding = finding.trim();
    if (Object.keys(body).length === 0) {
      onOpenChange(false);
      return;
    }
    update.mutate(
      { id: report.id, body },
      {
        onSuccess: () => {
          toast.success("Đã lưu. Chỉnh sửa được ghi vào review history.");
          onOpenChange(false);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Không lưu được thay đổi."),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit report</DialogTitle>
          <DialogDescription>
            Sửa title/finding sai do AI — mọi chỉnh sửa được log kèm reviewer.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <label htmlFor="report-edit-title" className="text-sm font-medium">
              Title
            </label>
            <Input
              id="report-edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="report-edit-finding" className="text-sm font-medium">
              Finding
            </label>
            <Textarea
              id="report-edit-finding"
              value={finding}
              onChange={(e) => setFinding(e.target.value)}
              rows={4}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={update.isPending || !title.trim()}>
            {update.isPending ? <Spinner data-icon="inline-start" /> : null}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Reports({
  initialRunId,
  initialReportId,
}: {
  initialRunId: string | null;
  initialReportId: string | null;
}) {
  const { product, productId } = useProduct();
  const qc = useQueryClient();
  const insights = useInsights();
  const [selectedId, setSelectedId] = useState<string | null>(initialReportId);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const items = useMemo(
    () =>
      (insights.data?.items ?? []).filter(
        (i) =>
          (!productId || i.product_id === productId) &&
          (statusFilter === "all" || i.status === statusFilter) &&
          (!search || i.title.toLowerCase().includes(search.toLowerCase())),
      ),
    [insights.data, productId, statusFilter, search],
  );

  const selected: InsightItem | undefined = useMemo(
    () => items.find((i) => i.id === (selectedId ?? items[0]?.id ?? null)),
    [items, selectedId],
  );

  // A run opened from the Data Graph — still investigating or waiting on G2.
  const runQuery = useAgentRun(initialRunId);
  const runData = runQuery.data ?? null;
  const pendingDraft = runData?.pending_approval ?? null;

  const generate = useGenerateActions();
  const me = useMe();
  const isPm = me.data?.role === "pm";
  const deleteInsight = useDeleteInsight();
  const [editingReport, setEditingReport] = useState<InsightItem | null>(null);
  const [confirmDeleteReport, setConfirmDeleteReport] = useState(false);
  // HAX G14 — the LLM can fail silently server-side; surface it here instead.
  const [genError, setGenError] = useState<string | null>(null);

  const afterDecision = (insightIds: string[]) => {
    void qc.invalidateQueries({ queryKey: ["insights"] });
    void qc.invalidateQueries({ queryKey: ["agent"] });
    if (insightIds[0]) setSelectedId(insightIds[0]);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={product?.name ?? "Reports"}
        description="Investigation draft và insight đã duyệt — mỗi kết luận gắn với bằng chứng truy ngược được."
      />

      <div className="grid min-w-0 gap-6 lg:grid-cols-[260px_minmax(0,1fr)_300px]">
        {/* Reports list */}
        <aside className="space-y-3">
          <Input
            placeholder="Search reports…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Status: all</SelectItem>
              <SelectItem value="pending">Needs review</SelectItem>
              <SelectItem value="investigating">Investigating</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="edited">Approved (edited)</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <div className="space-y-1">
            {initialRunId && pendingDraft ? (
              <button
                className="w-full rounded-lg border-2 border-pollen/60 bg-card p-3 text-left"
                onClick={() => setSelectedId(null)}
              >
                <span className="font-mono text-xs text-signal">
                  I-{initialRunId.slice(0, 8)}
                </span>
                <span className="block truncate text-sm font-medium">
                  {pendingDraft.insight.title}
                </span>
                <Badge className="mt-1">Needs review</Badge>
              </button>
            ) : null}
            {items.map((i) => (
              <button
                key={i.id}
                onClick={() => setSelectedId(i.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  selected?.id === i.id
                    ? "border-lichen bg-accent"
                    : "bg-card hover:bg-accent/60"
                }`}
              >
                <span className="block truncate font-heading text-sm">{i.title}</span>
                <span className="mt-1 block">
                  <StatusBadge status={i.status} />
                </span>
              </button>
            ))}
            {items.length === 0 && !pendingDraft ? (
              <p className="px-2 text-sm text-muted-foreground">
                No reports yet — ask a question in the Data Graph.
              </p>
            ) : null}
          </div>
        </aside>

        {/* Report body */}
        <div className="space-y-4">
          {initialRunId && pendingDraft && !selected ? (
            <>
              <ReportBody
                title={pendingDraft.insight.title}
                status="pending"
                finding={pendingDraft.insight.finding}
                findingConfidence={pendingDraft.insight.finding_confidence}
                hypothesis={{
                  statement: pendingDraft.insight.hypothesis_statement ?? null,
                  confidence: pendingDraft.insight.hypothesis_confidence ?? null,
                }}
                impact={pendingDraft.insight.impact ?? []}
                limitations={pendingDraft.insight.limitations ?? []}
                evidence={pendingDraft.evidence ?? []}
                runId={initialRunId}
              />
              <GateTwoBar runId={initialRunId} onDecided={afterDecision} />
              <Button variant="ghost" size="sm" asChild>
                <Link href="/data-graph">
                  <ArrowLeft data-icon="inline-start" />
                  Back to investigation
                </Link>
              </Button>
            </>
          ) : selected ? (
            <>
              <ReportBody
                title={selected.title}
                status={selected.status}
                finding={selected.finding}
                findingConfidence={selected.finding_confidence}
                hypothesis={selected.hypothesis}
                impact={(selected.impact ?? []) as string[]}
                limitations={(selected.limitations ?? []) as string[]}
                evidence={selected.evidence ?? []}
                runId={selected.run_id}
              />
              {(selected.status === "pending" || selected.status === "investigating") &&
              selected.run_id ? (
                <GateTwoBar runId={selected.run_id} onDecided={afterDecision} />
              ) : null}
              {isPm ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingReport(selected)}
                  >
                    <Pencil data-icon="inline-start" />
                    Edit report
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => setConfirmDeleteReport(true)}
                  >
                    <Trash2 data-icon="inline-start" />
                    Delete report
                  </Button>
                </div>
              ) : null}
              {selected.status === "approved" || selected.status === "edited" ? (
                <div className="rounded-xl border bg-card p-4">
                  <p className="text-sm font-semibold">Act on this report</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Generate proposed actions, review them in the Priority Matrix, then
                    accept explicitly (G3).
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      disabled={generate.isPending}
                      onClick={() =>
                        generate.mutate(selected.id, {
                          onSuccess: (res) => {
                            if (res.generation_error) {
                              // HAX G14 — the LLM failed; show why, offer retry via the same button.
                              setGenError(res.generation_error);
                              return;
                            }
                            setGenError(null);
                            if (res.actions_created === 0) {
                              toast.warning(
                                "No actions could be generated for this report — every function fell below the relevance threshold.",
                              );
                              return;
                            }
                            toast.success(
                              `${res.actions_created} action(s) proposed${
                                res.functions_skipped.length
                                  ? ` · skipped: ${res.functions_skipped.join(", ")}`
                                  : ""
                              }`,
                            );
                          },
                          onError: (err) =>
                            toast.error(
                              err instanceof Error ? err.message : "Generation failed",
                            ),
                        })
                      }
                    >
                      <Sparkles data-icon="inline-start" />
                      Generate actions
                    </Button>
                    <Button asChild>
                      <Link href={`/matrix?report=${selected.id}`}>
                        Open Priority Matrix
                      </Link>
                    </Button>
                  </div>
                  {genError ? (
                    <Alert variant="destructive" className="mt-3">
                      <FileText className="size-4" />
                      <AlertTitle>AI could not generate actions</AlertTitle>
                      <AlertDescription>
                        {genError} — press “Generate actions” to try again.
                      </AlertDescription>
                    </Alert>
                  ) : null}
                </div>
              ) : null}
              {selected.status === "rejected" ? (
                <Alert>
                  <FileText className="size-4" />
                  <AlertTitle>Rejected reports remain visible</AlertTitle>
                  <AlertDescription>
                    The decision, time, reviewer, and revision stay in the review
                    history.
                  </AlertDescription>
                </Alert>
              ) : null}
            </>
          ) : runQuery.isError && initialRunId ? (
            <Alert variant="destructive">
              <FileText className="size-4" />
              <AlertTitle>Could not load the investigation</AlertTitle>
              <AlertDescription>
                The connection dropped while reading this run. Nothing was lost —
                the investigation keeps running on the server.
              </AlertDescription>
              <div className="mt-2">
                <Button size="sm" variant="outline" onClick={() => void runQuery.refetch()}>
                  Check again
                </Button>
              </div>
            </Alert>
          ) : runQuery.isPending && initialRunId ? (
            <div className="rounded-xl border bg-card p-8 text-center">
              <Spinner />
              <p className="mt-3 text-sm text-muted-foreground">
                Investigation is running — the draft appears here when ready.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border bg-card p-8 text-center text-sm text-muted-foreground">
              Choose a report from the list, or ask a question in the{" "}
              <Link href="/data-graph" className="text-signal underline">
                Data Graph
              </Link>
              .
            </div>
          )}
        </div>

        {/* Review history rail */}
        <aside className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Review history
          </h2>
          <div className="rounded-xl border bg-card p-4 text-sm">
            {items.length === 0 ? (
              <p className="text-muted-foreground">No decisions yet.</p>
            ) : (
              <ul className="space-y-2">
                {items.slice(0, 8).map((i) => (
                  <li key={i.id} className="flex items-center justify-between gap-2">
                    <span className="min-w-0 flex-1 truncate">{i.title}</span>
                    <StatusBadge status={i.status} />
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              Every approval, edit, and rejection is recorded with its reviewer.
            </p>
          </div>
          {selected &&
          (selected.status === "approved" || selected.status === "edited") ? (
            <Button variant="outline" className="w-full" asChild>
              <Link href={`/matrix?report=${selected.id}`}>View actions</Link>
            </Button>
          ) : null}
        </aside>
      </div>

      <ReportEditDialog
        key={editingReport?.id ?? "none"}
        report={editingReport}
        open={editingReport != null}
        onOpenChange={(open) => !open && setEditingReport(null)}
      />

      <AlertDialog
        open={confirmDeleteReport}
        onOpenChange={setConfirmDeleteReport}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete report?</AlertDialogTitle>
            <AlertDialogDescription>
              Báo cáo “{selected?.title}” và toàn bộ actions liên quan sẽ bị xoá
              vĩnh viễn (không thể hoàn tác).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90"
              disabled={deleteInsight.isPending}
              onClick={(e) => {
                e.preventDefault();
                if (!selected) return;
                deleteInsight.mutate(selected.id, {
                  onSuccess: () => {
                    toast.success("Đã xoá báo cáo.");
                    setConfirmDeleteReport(false);
                    setSelectedId(null);
                  },
                  onError: (err) =>
                    toast.error(err instanceof Error ? err.message : "Xoá thất bại."),
                });
              }}
            >
              Delete permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <ReportsWithParams />
    </Suspense>
  );
}

function ReportsWithParams() {
  const params = useSearchParams();
  return (
    <Reports initialRunId={params.get("run")} initialReportId={params.get("report")} />
  );
}

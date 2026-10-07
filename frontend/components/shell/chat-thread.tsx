"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowUp,
  CircleCheck,
  FileText,
  History,
  Loader2,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AiTrace } from "@/components/ai/ai-trace";
import { useAgentRun, useCreateAgentRun } from "@/hooks/use-agent";
import { useRuns } from "@/hooks/use-analysis";
import { useProduct } from "@/hooks/use-product";
import { useChat } from "@/components/shell/chat-provider";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { shortDate } from "@/lib/graph";
import type { AgentRunStatusResponse } from "@/lib/types";

/** Signature motif: a woven nest holding the investigation until it hatches. */
function NestMark() {
  return (
    <svg viewBox="0 0 96 76" fill="none" className="w-16" aria-hidden>
      <path
        d="M48 30c-3.5-4.5-3.5-11 0-15.5M48 30c3.5-4.5 3.5-11 0-15.5"
        stroke="var(--lichen)"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <circle cx="41" cy="36" r="6.5" fill="var(--lichen)" fillOpacity="0.35" stroke="var(--lichen)" strokeWidth="1.6" />
      <circle cx="56" cy="36" r="6.5" fill="var(--signal)" fillOpacity="0.22" stroke="var(--signal)" strokeWidth="1.6" />
      <path
        d="M14 42c3.5 15.5 17 26 34 26s30.5-10.5 34-26"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <path
        d="M22 42c3 11 13 18 26 18s23-7 26-18"
        stroke="var(--signal)"
        strokeOpacity="0.55"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M31 42c2.2 6.5 8.5 10.5 17 10.5s14.8-4 17-10.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function RunCard({
  runId,
  question,
  onRetry,
}: {
  runId: string;
  question?: string | null;
  onRetry?: (question: string) => void;
}) {
  const run = useAgentRun(runId);
  const data: AgentRunStatusResponse | undefined = run.data;
  const pending = data?.pending_approval ?? null;
  const isRunning = data?.status === "running";
  const canRetry = onRetry != null && question != null;

  const retryButton = canRetry ? (
    <Button
      size="sm"
      variant="outline"
      className="h-7 text-xs"
      onClick={() => onRetry!(question!)}
    >
      <RefreshCw data-icon="inline-start" />
      Retry investigation
    </Button>
  ) : null;

  return (
    <div className="rounded-xl border bg-card p-3 text-left text-foreground shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-signal">
          Investigation {runId.slice(0, 8)}
        </span>
        {data ? (
          <Badge
            variant={
              data.status === "failed"
                ? "destructive"
                : data.status === "running"
                  ? "secondary"
                  : "outline"
            }
          >
            {data.status === "pending_approval" ? "needs review" : data.status}
          </Badge>
        ) : null}
      </div>

      {run.isError ? (
        <div className="mt-2 space-y-2">
          <p className="flex items-start gap-1.5 text-xs text-destructive">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" /> Connection lost while
            checking the investigation.
          </p>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={() => void run.refetch()}
          >
            <RefreshCw data-icon="inline-start" />
            Check again
          </Button>
        </div>
      ) : !data ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="size-3.5 animate-spin" /> Connecting to the investigation…
        </p>
      ) : data.status === "running" ? (
        <div className="mt-2 space-y-2">
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Investigating — gathering
            evidence. You can leave this panel.
          </p>
          {data.progress ? (
            <p className="font-mono text-[11px] text-muted-foreground">
              step {data.progress.iteration}/{data.progress.max_iterations}
              {data.progress.last_tool ? ` · ${data.progress.last_tool}` : " · planning"}
              {" · "}
              {data.progress.llm_calls_used}/{data.progress.llm_budget} LLM calls
            </p>
          ) : null}
          <AiTrace runId={runId} active={isRunning} startedAt={data.started_at} />
        </div>
      ) : data.status === "failed" ? (
        <div className="mt-2 space-y-2">
          <p className="flex items-start gap-1.5 text-xs text-destructive">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" /> {data.error ?? "The investigation failed."}
          </p>
          {retryButton}
        </div>
      ) : pending ? (
        <div className="mt-2 space-y-2">
          <h3 className="font-heading text-base leading-snug">{pending.insight.title}</h3>
          <p className="text-xs leading-relaxed">{pending.insight.finding}</p>
          {pending.evidence.length ? (
            <p className="font-mono text-[11px] text-muted-foreground">
              {pending.evidence.length} evidence item(s) recorded
            </p>
          ) : null}
          <p className="text-[11px] text-muted-foreground">
            The finding waits for your explicit review (G2) in Reports.
          </p>
          <Button size="sm" className="h-7 text-xs" asChild>
            <Link href={`/reports?run=${runId}`}>
              <FileText data-icon="inline-start" />
              Review in Reports
            </Link>
          </Button>
        </div>
      ) : (
        <p className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs">
          <CircleCheck className="size-3.5 shrink-0 text-lichen" /> Completed — the report is
          in{" "}
          <Link href="/reports" className="text-signal underline">
            Reports
          </Link>
          .
        </p>
      )}
    </div>
  );
}

type Entry = {
  runId: string;
  question: string | null;
  startError?: string;
  retrying?: boolean;
};

/**
 * The Chat tab content — the whole navigation dock becomes the chat: agent
 * header, thread and composer, sized for the panel. Stays mounted while the
 * panel shows Home so a running investigation keeps its thread.
 */
export function ChatThread() {
  const { chatOpen, activeRunId, openSeq } = useChat();
  const { product, productId } = useProduct();
  const createRun = useCreateAgentRun();
  const runs = useRuns();
  const [draft, setDraft] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [historyRunId, setHistoryRunId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Every openChat resets the thread: a run id seeds it as history, null starts fresh.
  useEffect(() => {
    if (!chatOpen) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- thread reset on open
    setEntries([]);
    setHistoryRunId(activeRunId);
  }, [openSeq, chatOpen]); // eslint-disable-line react-hooks/exhaustive-deps -- openSeq is the trigger

  // Keep the newest message in view (the viewport lives inside ScrollArea).
  useEffect(() => {
    const viewport = scrollRef.current?.querySelector<HTMLElement>(
      "[data-slot=scroll-area-viewport]",
    );
    viewport?.scrollTo({
      top: viewport.scrollHeight,
      behavior: "smooth",
    });
  }, [entries.length]);

  const send = async () => {
    const question = draft.trim();
    if (!productId || question.length < 3 || createRun.isPending) return;
    try {
      const { run_id } = await createRun.mutateAsync({
        product_id: productId,
        question,
      });
      setEntries((old) => [...old, { runId: run_id, question }]);
      setDraft("");
    } catch (err) {
      // HAX G14 — surface the real reason the run could not start.
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not start the investigation. Check the product and try again.";
      setEntries((old) => [
        ...old,
        { runId: "failed:" + Date.now(), question, startError: message },
      ]);
    }
  };

  /** HAX G7 — resubmit the same question without retyping it. */
  const startRetry = (failedRunId: string, question: string | null) => {
    if (!productId || !question || createRun.isPending) return;
    setEntries((old) =>
      old.map((e) =>
        e.runId === failedRunId ? { ...e, retrying: true, startError: undefined } : e,
      ),
    );
    createRun.mutate(
      { product_id: productId, question },
      {
        onSuccess: ({ run_id }) =>
          setEntries((old) =>
            old.map((e) =>
              e.runId === failedRunId
                ? { runId: run_id, question, startError: undefined, retrying: false }
                : e,
            ),
          ),
        onError: (err) =>
          setEntries((old) =>
            old.map((e) =>
              e.runId === failedRunId
                ? {
                    ...e,
                    retrying: false,
                    startError:
                      err instanceof ApiError
                        ? err.message
                        : "Could not start the investigation. Check the product and try again.",
                  }
                : e,
            ),
          ),
      },
    );
  };

  const recentRuns = (runs.data?.items ?? [])
    .filter((r) => r.prompt_version === "understand-v1")
    .slice(0, 8);

  const showHistory = historyRunId != null && entries.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* agent header */}
      <div className="flex shrink-0 items-center gap-2 border-b border-sidebar-border/60 px-4 py-2.5">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-lichen/20 font-heading text-sm font-semibold text-lichen">
          H
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-heading text-sm leading-tight">Happynest</p>
          <p className="truncate text-[11px] text-muted-foreground">
            Evidence-first investigations
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="rounded-md p-1.5 text-muted-foreground outline-none hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              disabled={recentRuns.length === 0}
              aria-label="Recent investigations"
              title="Recent investigations"
            >
              <History className="size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Recent investigations</DropdownMenuLabel>
            {recentRuns.map((run) => (
              <DropdownMenuItem
                key={run.id}
                onSelect={() => {
                  setEntries([]);
                  setHistoryRunId(run.id);
                }}
              >
                <span className="min-w-0 flex-1 truncate font-mono text-xs">
                  {run.id.slice(0, 8)} · {shortDate(run.started_at)}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <button
          className="rounded-md p-1.5 text-muted-foreground outline-none hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => {
            setEntries([]);
            setHistoryRunId(null);
            setDraft("");
          }}
          aria-label="New chat"
          title="New chat"
        >
          <Plus className="size-4" />
        </button>
      </div>

      {/* thread */}
      <ScrollArea ref={scrollRef} className="min-h-0 flex-1">
        <div className="flex min-h-full flex-col px-4 py-5">
          {showHistory ? <RunCard runId={historyRunId!} /> : null}

          {entries.length === 0 && !showHistory ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 py-6 text-center">
            <NestMark />
            <h2 className="font-heading text-lg leading-snug">
              What do you want to investigate?
            </h2>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Happynest digs through {product?.name ?? "your"} feedback, gathers
              evidence, and waits for your review before anything ships.
            </p>
            <p className="text-[11px] leading-relaxed text-muted-foreground/80">
              It can aggregate feedback, compare time periods, and run semantic
              search on the selected product. Scope is fixed when the
              investigation starts.
            </p>
            <div className="mt-1 grid w-full gap-1.5">
              {[
                "Why did accuracy complaints rise?",
                "Which problem hurts users the most?",
                "Summarize this week's regressions",
                "Which feature confuses new users?",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setDraft(s)}
                  className="flex items-center gap-2 rounded-xl border bg-card px-3 py-2 text-left text-xs text-foreground shadow-sm transition-colors hover:border-signal/50 hover:bg-accent/50"
                >
                  <Search className="size-3.5 shrink-0 text-muted-foreground" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="space-y-4">
          {entries.map((entry) => (
            <div key={entry.runId} className="space-y-2.5">
              {entry.question ? (
                <div className="flex justify-end">
                  <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-xs text-primary-foreground">
                    {entry.question}
                  </p>
                </div>
              ) : null}
              {entry.runId.startsWith("failed:") || entry.retrying ? (
                <div className="space-y-2 rounded-xl border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive">
                  {entry.retrying ? (
                    <p className="flex items-center gap-1.5">
                      <Loader2 className="size-3.5 animate-spin" /> Restarting the
                      investigation…
                    </p>
                  ) : (
                    <>
                      <p>
                        {entry.startError ??
                          "Could not start the investigation. Check the product and try again."}
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 border-destructive/40 text-xs text-destructive"
                        onClick={() => startRetry(entry.runId, entry.question)}
                        disabled={createRun.isPending}
                      >
                        <RefreshCw data-icon="inline-start" />
                        Retry investigation
                      </Button>
                    </>
                  )}
                </div>
              ) : (
                <RunCard
                  runId={entry.runId}
                  question={entry.question}
                  onRetry={(q) => startRetry(entry.runId, q)}
                />
              )}
            </div>
          ))}
          </div>
        </div>
      </ScrollArea>

      {/* composer */}
      <div className="shrink-0 px-4 pb-4 pt-2">
        <p className="mb-1.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <ShieldCheck className="size-3 shrink-0 text-lichen" />
          Investigations never act without your review.
        </p>
        <div className="rounded-2xl border bg-card p-2 text-foreground shadow-sm transition-colors focus-within:border-signal/50">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            placeholder="What are you wondering about…"
            rows={1}
            className="max-h-28 min-h-9 resize-none border-0 bg-transparent px-1.5 text-sm shadow-none focus-visible:ring-0"
            aria-label="Question"
          />
          <div className="flex items-center justify-between">
            <button
              className="rounded-full p-1.5 text-muted-foreground/70 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled
              title="Attachments — coming soon"
              aria-label="Attachments (coming soon)"
            >
              <Paperclip className="size-3.5" />
            </button>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-muted-foreground">Enter to send</span>
              <Button
                size="icon"
                className="size-8 rounded-full"
                onClick={() => void send()}
                disabled={draft.trim().length < 3 || createRun.isPending || !productId}
                aria-label="Send question"
              >
                {createRun.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <ArrowUp className="size-3.5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

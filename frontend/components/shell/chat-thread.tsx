"use client";
import { useEffect } from "react";
import {
  ArrowUp,
  History,
  Loader2,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuGroup,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker";
import { Message } from "@/components/ui/message";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import { InvestigationCard as RunCard } from "@/components/ai/investigation-card";
import { useInvestigationSession } from "@/hooks/use-investigation-session";
import { useCreateAgentRun } from "@/hooks/use-agent";
import { useRuns } from "@/hooks/use-analysis";
import { useProduct } from "@/hooks/use-product";
import { useChat } from "@/components/shell/chat-provider";
import { ApiError } from "@/lib/api";
import { shortDate } from "@/lib/graph";

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
 *
 * Dựng trên chat primitives của shadcn (MessageScroller / Message / Bubble /
 * Marker / InputGroup) trên surface tối `.chat-night` — mọi component bên trong
 * dùng semantic tokens gốc; class remap token trong globals.css đảo màu cả
 * subtree (primary → giấy, card/muted → pine elevation), không pha màu tay.
 */
export function ChatThread() {
  const { chatOpen, activeRunId, openSeq } = useChat();
  const { product, productId } = useProduct();
  const createRun = useCreateAgentRun();
  const runs = useRuns();
  const [draft, setDraft] = useInvestigationSession("chat-draft", productId, "");
  const [entries, setEntries] = useInvestigationSession<Entry[]>("chat-entries", productId, []);
  const [historyRunId, setHistoryRunId] = useInvestigationSession<string | null>("chat-history", productId, null);

  // Opening Chat resumes the current thread. Only an explicit history selection
  // changes the selected run; "New chat" is the only reset action.
  useEffect(() => {
    if (chatOpen && activeRunId) setHistoryRunId(activeRunId);
  }, [openSeq, chatOpen, activeRunId]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const showHistory = historyRunId != null && !entries.some(entry => entry.runId === historyRunId);

  return (
    <div className="chat-night flex min-h-0 flex-1 flex-col bg-background text-foreground">
      {/* agent header */}
      <div className="flex shrink-0 items-center gap-2 border-b px-4 py-2.5">
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
            <DropdownMenuGroup>{recentRuns.map((run) => (
              <DropdownMenuItem
                key={run.id}
                onSelect={() => {
                  setHistoryRunId(run.id);
                }}
              >
                <span className="min-w-0 flex-1 truncate text-xs">
                  Điều tra · {shortDate(run.started_at)} · {new Date(run.started_at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}
                </span>
              </DropdownMenuItem>
            ))}</DropdownMenuGroup>
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

      {/* thread — MessageScroller của shadcn lo follow/anchor/jump-to-latest */}
      <MessageScrollerProvider autoScroll>
        <MessageScroller className="min-h-0 flex-1">
          <MessageScrollerViewport>
            <MessageScrollerContent className="gap-6 px-4 py-5">
              {showHistory ? (
                <MessageScrollerItem>
                  <Message align="start">
                    <RunCard runId={historyRunId!} />
                  </Message>
                </MessageScrollerItem>
              ) : null}

              {entries.length === 0 && !showHistory ? (
                <MessageScrollerItem className="flex-1">
                  <div className="flex min-h-full flex-col items-center justify-center gap-3 py-6 text-center">
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
                          className="flex items-center gap-2 rounded-xl border bg-card px-3 py-2 text-left text-xs text-foreground shadow-sm transition-colors hover:bg-accent"
                        >
                          <Search className="size-3.5 shrink-0 text-muted-foreground" />
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </MessageScrollerItem>
              ) : null}

              {entries.map((entry) => (
                <MessageScrollerItem key={entry.runId} scrollAnchor={!!entry.question}>
                  <div className="flex flex-col gap-2.5">
                    {entry.question ? (
                      <Message align="end">
                        <Bubble variant="default" align="end" className="max-w-[85%]">
                          <BubbleContent className="text-xs">
                            {entry.question}
                          </BubbleContent>
                        </Bubble>
                      </Message>
                    ) : null}
                    {entry.runId.startsWith("failed:") || entry.retrying ? (
                      <Message align="start">
                        <Bubble variant="destructive" align="start" className="max-w-[95%]">
                          <BubbleContent className="w-full space-y-2 text-xs">
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
                          </BubbleContent>
                        </Bubble>
                      </Message>
                    ) : (
                      <Message align="start">
                        <RunCard
                          runId={entry.runId}
                          question={entry.question}
                          onRetry={() => startRetry(entry.runId, entry.question)}
                        />
                      </Message>
                    )}
                  </div>
                </MessageScrollerItem>
              ))}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      {/* composer */}
      <div className="shrink-0 px-4 pb-4 pt-2">
        <Marker className="mb-1.5 text-[10px] text-muted-foreground">
          <MarkerIcon className="text-lichen">
            <ShieldCheck />
          </MarkerIcon>
          <MarkerContent>Investigations never act without your review.</MarkerContent>
        </Marker>
        <InputGroup className="min-h-9 items-start rounded-2xl bg-muted/50 py-1.5">
          <InputGroupTextarea
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
            className="max-h-28 min-h-9"
            aria-label="Question"
          />
          <InputGroupAddon align="block-end" className="px-1.5 pb-0.5">
            <InputGroupButton
              disabled
              size="icon-xs"
              title="Attachments — coming soon"
              aria-label="Attachments (coming soon)"
              className="rounded-full text-muted-foreground/70"
            >
              <Paperclip />
            </InputGroupButton>
            <span className="ml-auto text-[10px] text-muted-foreground">Enter to send</span>
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
          </InputGroupAddon>
        </InputGroup>
      </div>
    </div>
  );
}

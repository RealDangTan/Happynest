"use client";
import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiFetch } from "@/lib/api";
import type { FeedbackListResponse, ImportRecord } from "@/lib/types";
import { useCreateAgentRun, useAgentRun } from "@/hooks/use-agent";
import { AiTrace } from "@/components/ai/ai-trace";
import { useProduct } from "@/hooks/use-product";
import { scopeLine, shortDate, topTopics, trendByDate } from "@/lib/graph";
import { PageHeader } from "@/components/page-header";

function useImportFeedbacks(importIds: string[]) {
  return useQuery({
    queryKey: ["data-graph", "feedbacks", importIds],
    queryFn: async () => {
      const results = await Promise.all(
        importIds.map((id) =>
          apiFetch<FeedbackListResponse>(`/api/feedbacks?import_id=${id}&limit=100`),
        ),
      );
      return results.flatMap((r) => r.items);
    },
    enabled: importIds.length > 0,
    staleTime: 30_000,
  });
}

function DatasetsRail({
  imports,
  checked,
  onToggle,
  onApply,
}: {
  imports: ImportRecord[];
  checked: Set<string>;
  onToggle: (id: string) => void;
  onApply: () => void;
}) {
  return (
    <aside className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Datasets
      </h2>
      <div className="space-y-2">
        {imports.map((item) => (
          <label
            key={item.id}
            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-accent/60"
          >
            <Checkbox
              checked={checked.has(item.id)}
              onCheckedChange={() => onToggle(item.id)}
              aria-label={`Dataset ${item.original_filename}`}
            />
            <span className="min-w-0 flex-1 truncate">
              {item.original_filename ?? item.id.slice(0, 8)}
            </span>
          </label>
        ))}
        {imports.length === 0 ? (
          <p className="px-2 text-sm text-muted-foreground">No imported datasets yet.</p>
        ) : null}
      </div>
      <Button size="sm" variant="outline" onClick={onApply} disabled={checked.size === 0}>
        Apply scope
      </Button>
      <Button size="sm" variant="ghost" asChild>
        <Link href="/vault">Open Vault</Link>
      </Button>
    </aside>
  );
}

function WordCloud({
  words,
  onSelect,
}: {
  words: { topic: string; count: number }[];
  onSelect: (topic: string) => void;
}) {
  const max = Math.max(...words.map((w) => w.count), 1);
  return (
    <div className="flex flex-wrap items-baseline justify-center gap-x-5 gap-y-2 p-8">
      {words.map(({ topic, count }) => {
        const scale = 0.8 + (count / max) * 1.6;
        return (
          <button
            key={topic}
            onClick={() => onSelect(topic)}
            style={{ fontSize: `${scale}rem` }}
            className={`font-heading transition-colors hover:text-signal ${
              count / max > 0.6 ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {topic}
          </button>
        );
      })}
    </div>
  );
}

function Trends({ points }: { points: { date: string; count: number }[] }) {
  const max = Math.max(...points.map((p) => p.count), 1);
  return (
    <div className="flex h-56 items-end gap-2 p-6">
      {points.map((p) => (
        <div key={p.date} className="flex flex-1 flex-col items-center gap-1">
          <span className="font-mono text-xs text-muted-foreground">{p.count}</span>
          <div
            className="w-full rounded-t bg-chart-2/80"
            style={{ height: `${(p.count / max) * 160}px` }}
            title={`${p.date}: ${p.count}`}
          />
          <span className="font-mono text-[10px] text-muted-foreground">
            {shortDate(p.date)}
          </span>
        </div>
      ))}
      {points.length === 0 ? (
        <p className="text-sm text-muted-foreground">No dated feedback in this scope.</p>
      ) : null}
    </div>
  );
}

function ActivityTrace({
  runId,
  scopeSnapshot,
  onOpenReport,
  onRetry,
}: {
  runId: string | null;
  scopeSnapshot: string | null;
  onOpenReport: (runId: string) => void;
  onRetry: () => void;
}) {
  const run = useAgentRun(runId);
  const status = run.data?.status;
  const pending = run.data?.pending_approval ?? null;
  const isRunning = status === "running";

  return (
    <aside className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Activity trace
      </h2>
      {!runId ? (
        <p className="text-sm text-muted-foreground">
          Ask a question about this data to start an investigation.
        </p>
      ) : (
        <div className="rounded-xl border bg-card p-3">
          <p className="font-mono text-xs text-signal">
            Investigation {runId.slice(0, 8)}
          </p>
          {run.isError ? (
            <div className="mt-2 space-y-2">
              <p className="text-sm text-destructive">
                Connection lost while checking the investigation.
              </p>
              <Button size="sm" variant="outline" className="w-full" onClick={() => void run.refetch()}>
                Check again
              </Button>
            </div>
          ) : (
            <ul className="mt-2 space-y-1.5 text-sm">
              <li className="flex items-center gap-2">
                <Badge variant="outline" className="h-4 w-4 p-0" />
                Question received
              </li>
              {scopeSnapshot ? (
                <li className="font-mono text-xs text-muted-foreground">{scopeSnapshot}</li>
              ) : null}
              {isRunning ? (
                <li className="flex items-center gap-2">
                  <Spinner className="size-3" /> Investigating…
                </li>
              ) : null}
              {status === "pending_approval" || status === "completed" ? (
                <>
                  <li className="flex items-center gap-2">
                    <Badge variant="secondary" className="h-4 w-4 rounded-full p-0" />
                    Evidence gathered
                    {pending?.evidence?.length ? (
                      <span className="font-mono text-xs text-signal">
                        {pending.evidence.length}
                      </span>
                    ) : null}
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge variant="secondary" className="h-4 w-4 rounded-full p-0" />
                    Draft ready
                  </li>
                </>
              ) : null}
              {status === "failed" ? (
                <li className="text-destructive">Failed: {run.data?.error ?? "unknown"}</li>
              ) : null}
            </ul>
          )}
          {isRunning && run.data ? (
            <AiTrace
              runId={runId!}
              active
              startedAt={run.data.started_at}
              className="mt-2"
            />
          ) : null}
          <p className="mt-2 text-xs text-muted-foreground">
            Scope fixed at investigation start. Chart filters cannot change it.
          </p>
          {status === "failed" ? (
            <Button size="sm" variant="outline" className="mt-3 w-full" onClick={onRetry}>
              Retry with the same question
            </Button>
          ) : null}
          {status === "pending_approval" || status === "completed" ? (
            <Button size="sm" className="mt-3 w-full" onClick={() => onOpenReport(runId!)}>
              Open report
            </Button>
          ) : null}
        </div>
      )}
    </aside>
  );
}

function DataGraph({ initialImportId, initialTopic }: { initialImportId: string | null; initialTopic: string }) {
  const { product, productId } = useProduct();
  const router = useRouter();
  const importsQuery = useQuery({
    queryKey: ["imports", "data-graph", productId],
    queryFn: () =>
      apiFetch<{ items: ImportRecord[] }>(
        `/api/imports?limit=50&product_id=${productId}&status=imported`,
      ),
    enabled: productId != null,
    staleTime: 30_000,
  });
  const imports = importsQuery.data?.items ?? [];

  // null = "no explicit scope yet" → derived default of all imports.
  const [checked, setChecked] = useState<Set<string> | null>(
    initialImportId ? new Set([initialImportId]) : null,
  );
  const [scope, setScope] = useState<string[] | null>(
    initialImportId ? [initialImportId] : null,
  );
  const effectiveChecked = checked ?? new Set(imports.map((i) => i.id));
  const effectiveScope = scope ?? imports.map((i) => i.id);
  const [tab, setTab] = useState("cloud");
  const [selectedTopic, setSelectedTopic] = useState<string>(initialTopic);
  const [question, setQuestion] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [scopeSnapshot, setScopeSnapshot] = useState<string | null>(null);

  const feedbacks = useImportFeedbacks(effectiveScope);
  const items = useMemo(
    () => (feedbacks.data ?? []).filter((f) => Boolean(f.ai_analysis)),
    [feedbacks.data],
  );
  const pendingExcluded = (feedbacks.data ?? []).length - items.length;
  const dates = items.map((f) => f.occurred_at.slice(0, 10)).sort();

  const words = topTopics(items);
  const trends = trendByDate(items);
  const matched = selectedTopic
    ? items.filter((f) => f.ai_analysis?.topics?.includes(selectedTopic))
    : [];

  const createRun = useCreateAgentRun();

  const askAI = async () => {
    if (!productId || question.trim().length < 3) return;
    setScopeSnapshot(
      scopeLine(
        effectiveScope.length,
        dates[0] ?? "",
        dates.at(-1) ?? "",
        items.length,
        pendingExcluded,
      ),
    );
    try {
      const { run_id } = await createRun.mutateAsync({
        product_id: productId,
        question: question.trim(),
      });
      setRunId(run_id);
      toast.success("Investigation started — trace appears on the right.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start investigation");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={product?.name ?? "Data Graph"}
        description={
          effectiveScope.length > 0
            ? scopeLine(effectiveScope.length, dates[0] ?? "—", dates.at(-1) ?? "—", items.length, pendingExcluded)
            : "Apply a dataset scope to explore."
        }
      />

      <div className="grid min-w-0 gap-6 lg:grid-cols-[200px_minmax(0,1fr)_260px]">
        <DatasetsRail
          imports={imports}
          checked={effectiveChecked}
          onToggle={(id) =>
            setChecked(() => {
              const next = new Set(effectiveChecked);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              return next;
            })
          }
          onApply={() => {
            setChecked(new Set(effectiveChecked));
            setScope([...effectiveChecked]);
            setSelectedTopic("");
          }}
        />

        <div className="space-y-4">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="cloud">Word cloud</TabsTrigger>
              <TabsTrigger value="trends">Trends</TabsTrigger>
              <TabsTrigger value="topics">Topics</TabsTrigger>
              <TabsTrigger value="table">Table</TabsTrigger>
            </TabsList>
            <TabsContent value="cloud" className="rounded-xl border bg-card">
              {feedbacks.isPending ? (
                <div className="p-8 text-center">
                  <Spinner />
                </div>
              ) : words.length ? (
                <>
                  <WordCloud words={words} onSelect={setSelectedTopic} />
                  <p className="pb-4 text-center text-xs text-muted-foreground">
                    Word size = frequency in this scope.
                  </p>
                </>
              ) : (
                <p className="p-8 text-center text-sm text-muted-foreground">
                  No analyzed feedback in this scope yet — analyze pending items in the Vault.
                </p>
              )}
            </TabsContent>
            <TabsContent value="trends" className="rounded-xl border bg-card">
              <Trends points={trends} />
            </TabsContent>
            <TabsContent value="topics" className="rounded-xl border bg-card p-6">
              <ul className="space-y-3">
                {words.map(({ topic, count }) => (
                  <li key={topic} className="flex items-center gap-3">
                    <button
                      className="w-32 text-left text-sm font-medium hover:text-signal"
                      onClick={() => setSelectedTopic(topic)}
                    >
                      {topic}
                    </button>
                    <div className="h-3 flex-1 rounded bg-secondary">
                      <div
                        className="h-3 rounded bg-chart-1"
                        style={{ width: `${(count / (words[0]?.count || 1)) * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-muted-foreground">{count}</span>
                  </li>
                ))}
                {words.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No topics yet.</p>
                ) : null}
              </ul>
            </TabsContent>
            <TabsContent value="table" className="rounded-xl border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Feedback</TableHead>
                    <TableHead className="w-32">Topic</TableHead>
                    <TableHead className="w-24">Sentiment</TableHead>
                    <TableHead className="w-24">Occurred</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.slice(0, 50).map((f) => (
                    <TableRow key={f.id}>
                      <TableCell className="max-w-md break-words">
                        <span className="line-clamp-1 text-sm">{f.feedback_text}</span>
                      </TableCell>
                      <TableCell className="break-words text-sm">
                        {f.ai_analysis?.topics?.[0] ?? "—"}
                      </TableCell>
                      <TableCell className="text-sm">{f.ai_analysis?.sentiment ?? "—"}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {shortDate(f.occurred_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>
          </Tabs>

          {selectedTopic ? (
            <section className="rounded-xl border bg-card p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">
                  Selected: <span className="text-signal">{selectedTopic}</span>
                </h3>
                <Button size="sm" variant="ghost" onClick={() => setSelectedTopic("")}>
                  Clear
                </Button>
              </div>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {matched.length} feedback {matched.length === 1 ? "item" : "items"}
              </p>
              <ul className="mt-3 max-h-60 space-y-2 overflow-y-auto">
                {matched.slice(0, 20).map((f) => (
                  <li key={f.id} className="rounded-lg border bg-secondary/30 p-2 text-sm">
                    <span className="font-mono text-xs text-signal">
                      F-{f.id.slice(0, 8)}
                    </span>{" "}
                    {f.feedback_text}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border bg-card p-4">
            <h3 className="text-sm font-semibold">Ask about this data</h3>
            <div className="mt-2 flex gap-2">
              <Input
                placeholder="e.g. Why did accuracy complaints rise?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void askAI()}
              />
              <Button onClick={() => void askAI()} disabled={question.trim().length < 3 || createRun.isPending}>
                {createRun.isPending ? <Spinner data-icon="inline-start" /> : <Send data-icon="inline-start" />}
                Ask AI
              </Button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              The investigation keeps the scope fixed at start and reports usage
              before acting. Evidence links to specific feedback.
            </p>
          </section>
        </div>

        <ActivityTrace
          runId={runId}
          scopeSnapshot={scopeSnapshot}
          onOpenReport={(id) => router.push(`/reports?run=${id}`)}
          onRetry={() => void askAI()}
        />
      </div>
    </div>
  );
}

export default function DataGraphPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <DataGraphWithParams />
    </Suspense>
  );
}

function DataGraphWithParams() {
  const params = useSearchParams();
  return (
    <DataGraph
      initialImportId={params.get("import")}
      initialTopic={params.get("topic") ?? ""}
    />
  );
}

"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useLegacyTable,
  type LegacyColumnDef,
} from "@tanstack/react-table/legacy"
import { Send } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { InputGroup, InputGroupInput } from "@/components/ui/input-group"
import { Spinner } from "@/components/ui/spinner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  DataTableToolbar,
} from "@/components/data-table"
import { apiFetch } from "@/lib/api"
import type { Feedback, FeedbackListResponse, ImportRecord } from "@/lib/types"
import { useCreateAgentRun } from "@/hooks/use-agent"
import { InvestigationCard } from "@/components/ai/investigation-card"
import { useInvestigationSession } from "@/hooks/use-investigation-session"
import { useProduct } from "@/hooks/use-product"
import { useTaxonomy } from "@/hooks/use-taxonomy"
import {
  multiSelectFilterFn,
  severitySortFn,
} from "@/lib/table-sorts"
import { scopeLine, shortDate, topTopics, topicLabeler, trendByDate } from "@/lib/graph"
import { PageHeader } from "@/components/page-header"

function useImportFeedbacks(importIds: string[]) {
  return useQuery({
    queryKey: ["data-graph", "feedbacks", importIds],
    queryFn: async () => {
      const results = await Promise.all(
        importIds.map((id) =>
          apiFetch<FeedbackListResponse>(
            `/api/feedbacks?import_id=${id}&limit=100`
          )
        )
      )
      return results.flatMap((r) => r.items)
    },
    enabled: importIds.length > 0,
    staleTime: 30_000,
  })
}

/** Tab Table — duyệt TOÀN BỘ items trong scope (trước đây cắt ngầm 50 dòng)
 * với search/sort/facet/phân trang client-side. */
function ScopeTable({
  items,
  topicLabel,
}: {
  items: Feedback[]
  topicLabel: (topic: string) => string
}) {
  const columns = useMemo<LegacyColumnDef<Feedback>[]>(
    () => [
      {
        id: "content",
        enableSorting: false,
        enableHiding: false,
        meta: { thClassName: "w-[42%]" },
        header: "Feedback",
        cell: ({ row }) => (
          <span className="line-clamp-1 block max-w-md text-sm">
            {row.original.feedback_text}
          </span>
        ),
      },
      {
        id: "topics",
        enableSorting: false,
        meta: { label: "Topic" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Topic" />
        ),
        cell: ({ row }) => {
          const first = row.original.ai_analysis?.topics?.[0]
          return first ? (
            <span className="block max-w-40 truncate text-sm" title={first}>
              {topicLabel(first)}
            </span>
          ) : (
            "—"
          )
        },
      },
      {
        id: "sentiment",
        accessorFn: (f: Feedback) => f.ai_analysis?.sentiment ?? "",
        enableSorting: false,
        filterFn: multiSelectFilterFn,
        meta: { label: "Sentiment" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Sentiment" />
        ),
        cell: ({ row }) => (
          <SentimentIndicator value={row.original.ai_analysis?.sentiment} />
        ),
      },
      {
        id: "severity",
        accessorFn: (f: Feedback) => f.ai_analysis?.severity ?? "",
        filterFn: multiSelectFilterFn,
        sortingFn: severitySortFn,
        sortDescFirst: true,
        meta: { label: "Severity" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Severity" />
        ),
        cell: ({ row }) => {
          const severity = row.original.ai_analysis?.severity
          return severity ? (
            <Badge variant={severity === "critical" || severity === "high" ? "destructive" : "secondary"}>
              {severity}
            </Badge>
          ) : (
            "—"
          )
        },
      },
      {
        id: "occurred_at",
        accessorFn: (f: Feedback) => f.occurred_at,
        meta: { label: "Occurred" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Occurred" />
        ),
        cell: ({ row }) => (
          <span className="font-mono text-xs whitespace-nowrap">
            {shortDate(row.original.occurred_at)}
          </span>
        ),
      },
    ],
    [topicLabel],
  )

  const table = useLegacyTable({
    data: items,
    columns,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    globalFilterFn: "includesString",
    initialState: {
      sorting: [{ id: "occurred_at", desc: true }],
      pagination: { pageIndex: 0, pageSize: 20 },
    },
  })

  return (
    <Card className="gap-3 py-4">
      <CardContent className="flex flex-col gap-3 px-(--card-spacing)">
        <DataTableToolbar
          table={table}
          filters={[
            {
              columnId: "sentiment",
              title: "Sentiment",
              options: ["positive", "neutral", "negative", "mixed"].map(
                (value) => ({ value, label: value[0].toUpperCase() + value.slice(1) }),
              ),
            },
          ]}
        />
        <DataTable table={table} />
        <DataTablePagination table={table} />
      </CardContent>
    </Card>
  )
}

function DatasetsRail({
  imports,
  checked,
  onToggle,
  onApply,
}: {
  imports: ImportRecord[]
  checked: Set<string>
  onToggle: (id: string) => void
  onApply: () => void
}) {
  return (
    <Card size="sm" className="self-start">
      <CardHeader>
        <CardTitle>Datasets</CardTitle>
        <CardDescription>Chọn import để giới hạn phạm vi</CardDescription>
      </CardHeader>
      <CardContent className="gap-2">
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
              {item.original_filename ?? "Lô dữ liệu"}
            </span>
          </label>
        ))}
        {imports.length === 0 ? (
          <p className="px-2 text-sm text-muted-foreground">
            No imported datasets yet.
          </p>
        ) : null}
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={onApply}
          disabled={checked.size === 0}
        >
          Apply scope
        </Button>
        <Button size="sm" variant="ghost" asChild>
          <Link href="/vault">Open Vault</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

function WordCloud({
  words,
  label,
  onSelect,
}: {
  words: { topic: string; count: number }[]
  label: (topic: string) => string
  onSelect: (topic: string) => void
}) {
  const max = Math.max(...words.map((w) => w.count), 1)
  return (
    <div className="flex flex-wrap items-baseline justify-center gap-x-5 gap-y-2 p-8">
      {words.map(({ topic, count }) => {
        const scale = 0.8 + (count / max) * 1.6
        return (
          <button
            key={topic}
            onClick={() => onSelect(topic)}
            title={label(topic) !== topic ? topic : undefined}
            style={{ fontSize: `${scale}rem` }}
            className={`font-heading transition-colors hover:text-signal ${
              count / max > 0.6 ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {label(topic)}
          </button>
        )
      })}
    </div>
  )
}

function Trends({ points }: { points: { date: string; count: number }[] }) {
  const max = Math.max(...points.map((p) => p.count), 1)
  return (
    <div className="flex h-56 items-end gap-2 p-6">
      {points.map((p) => (
        <div key={p.date} className="flex flex-1 flex-col items-center gap-1">
          <span className="font-mono text-xs text-muted-foreground">
            {p.count}
          </span>
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
        <p className="text-sm text-muted-foreground">
          No dated feedback in this scope.
        </p>
      ) : null}
    </div>
  )
}

function DataGraph({
  initialImportId,
  initialTopic,
  initialRunId,
}: {
  initialImportId: string | null
  initialTopic: string
  initialRunId: string | null
}) {
  const { product, productId } = useProduct()
  const router = useRouter()
  const taxonomyQuery = useTaxonomy(productId)
  const topicLabel = useMemo(
    () => topicLabeler(taxonomyQuery.data?.items ?? []),
    [taxonomyQuery.data]
  )
  const importsQuery = useQuery({
    queryKey: ["imports", "data-graph", productId],
    queryFn: () =>
      apiFetch<{ items: ImportRecord[] }>(
        `/api/imports?limit=50&product_id=${productId}&status=imported`
      ),
    enabled: productId != null,
    staleTime: 30_000,
  })
  const imports = importsQuery.data?.items ?? []

  // null = "no explicit scope yet" → derived default of all imports.
  const [checked, setChecked] = useState<Set<string> | null>(
    initialImportId ? new Set([initialImportId]) : null
  )
  const [scope, setScope] = useInvestigationSession<string[] | null>("scope", productId, initialImportId ? [initialImportId] : null)
  const effectiveChecked = checked ?? new Set(scope ?? imports.map((i) => i.id))
  const effectiveScope = scope ?? imports.map((i) => i.id)
  const [tab, setTab] = useInvestigationSession("view", productId, "cloud")
  const [selectedTopic, setSelectedTopic] = useInvestigationSession<string>("topic", productId, initialTopic)
  const [question, setQuestion] = useInvestigationSession("question", productId, "")
  const [savedRunId, setRunId] = useInvestigationSession<string | null>("run", productId, null)
  const [runQuestion, setRunQuestion] = useInvestigationSession("run-question", productId, "")
  const runId = initialRunId ?? savedRunId

  const feedbacks = useImportFeedbacks(effectiveScope)
  const items = useMemo(
    () => (feedbacks.data ?? []).filter((f) => Boolean(f.ai_analysis)),
    [feedbacks.data]
  )
  const pendingExcluded = (feedbacks.data ?? []).length - items.length
  const dates = items.map((f) => f.occurred_at.slice(0, 10)).sort()

  const words = topTopics(items)
  const trends = trendByDate(items)
  const matched = selectedTopic
    ? items.filter((f) => f.ai_analysis?.topics?.includes(selectedTopic))
    : []

  const createRun = useCreateAgentRun()

  const askAI = async () => {
    if (!productId || question.trim().length < 3) return
    try {
      const { run_id } = await createRun.mutateAsync({
        product_id: productId,
        question: question.trim(),
      })
      setRunId(run_id)
      setRunQuestion(question.trim())
      router.replace(`/data-graph?run=${run_id}`, { scroll: false })
      toast.success("Đã bắt đầu điều tra. Kết quả và duyệt hiển thị ngay bên dưới.")
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Could not start investigation"
      )
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={product?.name ?? "Data Graph"}
        documentTitle="Data Graph"
        description={
          effectiveScope.length > 0
            ? scopeLine(
                effectiveScope.length,
                dates[0] ?? "—",
                dates.at(-1) ?? "—",
                items.length,
                pendingExcluded
              )
            : "Apply a dataset scope to explore."
        }
      />

      <div className="grid min-w-0 gap-6 lg:grid-cols-[200px_minmax(0,1fr)]">
        <DatasetsRail
          imports={imports}
          checked={effectiveChecked}
          onToggle={(id) =>
            setChecked(() => {
              const next = new Set(effectiveChecked)
              if (next.has(id)) next.delete(id)
              else next.add(id)
              return next
            })
          }
          onApply={() => {
            setChecked(new Set(effectiveChecked))
            setScope([...effectiveChecked])
            setSelectedTopic("")
          }}
        />

        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Hỏi và duyệt kết luận</CardTitle>
              <CardDescription>
                Đặt câu hỏi về sản phẩm đang chọn. Theo dõi bằng chứng và duyệt kết luận ngay tại đây.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <InputGroup className="flex-1">
                  <InputGroupInput
                    placeholder="Ví dụ: Vấn đề nào đang ảnh hưởng người dùng nhiều nhất?"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && void askAI()}
                  />
                </InputGroup>
                <Button
                  onClick={() => void askAI()}
                  disabled={question.trim().length < 3 || createRun.isPending}
                >
                  {createRun.isPending ? (
                    <Spinner data-icon="inline-start" />
                  ) : (
                    <Send data-icon="inline-start" />
                  )}
                  Bắt đầu điều tra
                </Button>
              </div>
            </CardContent>
          </Card>
          {runId ? <InvestigationCard key={runId} runId={runId} question={savedRunId === runId ? runQuestion : null} onRetry={() => void askAI()} /> : null}

          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="cloud">Word cloud</TabsTrigger>
              <TabsTrigger value="trends">Trends</TabsTrigger>
              <TabsTrigger value="topics">Topics</TabsTrigger>
              <TabsTrigger value="table">Table</TabsTrigger>
            </TabsList>
            <TabsContent value="cloud">
              <Card>
                <CardContent className="p-0">
                  {feedbacks.isPending ? (
                    <div className="p-8 text-center">
                      <Spinner />
                    </div>
                  ) : words.length ? (
                    <>
                      <WordCloud
                        words={words}
                        label={topicLabel}
                        onSelect={setSelectedTopic}
                      />
                      <p className="pb-4 text-center text-xs text-muted-foreground">
                        Word size = frequency in this scope.
                      </p>
                    </>
                  ) : (
                    <p className="p-8 text-center text-sm text-muted-foreground">
                      No analyzed feedback in this scope yet — analyze pending
                      items in the Vault.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="trends">
              <Card>
                <CardContent className="p-0">
                  <Trends points={trends} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="topics">
              <Card>
                <CardContent className="p-0">
                  <ul className="flex flex-col gap-3 p-6">
                      {words.map(({ topic, count }) => (
                        <li key={topic} className="flex items-center gap-3">
                          <button
                            className="w-32 text-left text-sm font-medium hover:text-signal"
                            onClick={() => setSelectedTopic(topic)}
                          >
                            {topicLabel(topic)}
                          </button>
                        <div className="h-3 flex-1 rounded bg-secondary">
                          <div
                            className="h-3 rounded bg-chart-1"
                            style={{
                              width: `${(count / (words[0]?.count || 1)) * 100}%`,
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs text-muted-foreground">
                          {count}
                        </span>
                      </li>
                    ))}
                    {words.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No topics yet.
                      </p>
                    ) : null}
                  </ul>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="table">
              {feedbacks.isPending ? (
                <Card>
                  <CardContent className="flex justify-center p-8">
                    <Spinner />
                  </CardContent>
                </Card>
              ) : items.length ? (
                <ScopeTable items={items} topicLabel={topicLabel} />
              ) : (
                <Card>
                  <CardContent className="p-0">
                    <p className="p-8 text-center text-sm text-muted-foreground">
                      No analyzed feedback in this scope yet — analyze pending
                      items in the Vault.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>

          {selectedTopic ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">
                  Selected:{" "}
                  <span className="text-signal">{topicLabel(selectedTopic)}</span>

                </CardTitle>
                <CardAction>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setSelectedTopic("")}
                  >
                    Clear
                  </Button>
                </CardAction>
                <CardDescription className="font-mono text-xs">
                  {matched.length} feedback{" "}
                  {matched.length === 1 ? "item" : "items"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="flex max-h-60 flex-col gap-2 overflow-y-auto">
                  {matched.slice(0, 20).map((f) => (
                    <li
                      key={f.id}
                      className="rounded-lg border bg-secondary/30 p-2 text-sm"
                    >
                      {f.feedback_text}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}


        </div>

      </div>
    </div>
  )
}

export default function DataGraphPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <DataGraphWithParams />
    </Suspense>
  )
}

function DataGraphWithParams() {
  const params = useSearchParams()
  const { productId } = useProduct()
  return (
    <DataGraph
      key={productId}
      initialRunId={params.get("run")}
      initialImportId={params.get("import")}
      initialTopic={params.get("topic") ?? ""}
    />
  )
}

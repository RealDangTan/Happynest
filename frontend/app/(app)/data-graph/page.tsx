"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import { Suspense, useEffect, useMemo, useRef, useState } from "react"
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
import { Send, Sparkles } from "lucide-react"
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
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
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
import type { Feedback, FeedbackListResponse, ImportRecord, Severity } from "@/lib/types"
import { useCreateAgentRun } from "@/hooks/use-agent"
import { InvestigationCard } from "@/components/ai/investigation-card"
import { FeedbackTrends, feedbackDay, type TrendRange } from "@/components/feedback-trends"
import { useInvestigationSession } from "@/hooks/use-investigation-session"
import { useProduct } from "@/hooks/use-product"
import { useTaxonomy } from "@/hooks/use-taxonomy"
import {
  multiSelectFilterFn,
  severitySortFn,
} from "@/lib/table-sorts"
import { scopeLine, shortDate, topTopics, topicLabeler } from "@/lib/graph"
import { PageHeader } from "@/components/page-header"
import { NextStepBar } from "@/components/journey/next-step-bar"
import { useT } from "@/lib/i18n"
import { SEVERITY_TONE } from "@/lib/tone"
import { SEVERITY_LABEL } from "@/lib/labels"
import { cn } from "@/lib/utils"

function useImportFeedbacks(importIds: string[]) {
  return useQuery({
    queryKey: ["data-graph", "feedbacks", "scope", importIds],
    queryFn: async () => {
      const results = await Promise.all(
        importIds.map((id) =>
          apiFetch<FeedbackListResponse>(
            `/api/feedbacks?import_id=${id}&limit=100`
          )
        )
      )
      return {
        items: results.flatMap((r) => r.items),
        partial: results.some((r) => r.total > r.items.length),
      }
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
            <Badge variant={SEVERITY_TONE[severity] ?? "secondary"}>
              {SEVERITY_LABEL.vi[severity as Severity] ?? severity}
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
        <CardTitle>Bộ dữ liệu</CardTitle>
        <CardDescription>Chọn file để giới hạn phạm vi xem</CardDescription>
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
            Chưa có file nào được nhập.
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
          Áp dụng phạm vi
        </Button>
        <Button size="sm" variant="ghost" asChild>
          <Link href="/vault">Mở Kho phản hồi</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

const CLOUD_INK = [
  "text-leaf-ink",
  "text-sky-ink",
  "text-coral-ink",
  "text-iris-ink",
  "text-sun-ink",
]

function WordCloud({
  words,
  label,
  selected,
  onSelect,
}: {
  words: { topic: string; count: number }[]
  label: (topic: string) => string
  selected: string
  onSelect: (topic: string) => void
}) {
  const max = Math.max(...words.map((w) => w.count), 1)
  return (
    <div className="flex flex-wrap items-baseline justify-center gap-x-5 gap-y-2 p-8">
      {words.map(({ topic, count }, i) => {
        const scale = 0.8 + (count / max) * 1.6
        return (
          <button
            key={topic}
            onClick={() => onSelect(topic === selected ? "" : topic)}
            aria-pressed={topic === selected}
            title={`${label(topic)} · ${count} phản hồi`}
            style={{ fontSize: `${scale}rem` }}
            className={cn(
              "rounded-md px-1 font-heading underline-offset-4 transition-[color,opacity,background-color] hover:underline focus-visible:outline-2 focus-visible:outline-ring",
              CLOUD_INK[i % CLOUD_INK.length],
              selected && topic !== selected && "opacity-40",
              topic === selected && "bg-accent underline",
            )}
          >
            {label(topic)}
          </button>
        )
      })}
    </div>
  )
}

/** Chủ đề đang chọn + phản hồi gốc trong cùng màn (mẫu Dovetail "Themes"):
 * người dùng đọc được lời người dùng thật trước khi hỏi AI, và mở chi tiết từng
 * phản hồi mà không mất phạm vi/chủ đề đang xem. */
function TopicPanel({
  topic,
  label,
  items,
  onClear,
  onAsk,
}: {
  topic: string
  label: string
  items: Feedback[]
  onClear: () => void
  onAsk: () => void
}) {
  const negative = items.filter((f) => f.ai_analysis?.sentiment === "negative").length
  return (
    <Card size="sm" className="self-start xl:sticky xl:top-20">
      <CardHeader>
        <p className="text-xs text-muted-foreground">Chủ đề đang xem</p>
        <CardTitle className="font-heading text-lg text-signal" title={label !== topic ? topic : undefined}>
          {label}
        </CardTitle>
        <CardAction>
          <Button size="sm" variant="ghost" onClick={onClear}>
            Bỏ chọn
          </Button>
        </CardAction>
        <CardDescription className="font-mono text-xs">
          {items.length} phản hồi · {negative} tiêu cực
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Button size="sm" onClick={onAsk}>
          <Sparkles data-icon="inline-start" />
          Hỏi AI về chủ đề này
        </Button>
        <ul className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto pr-1" aria-label={`Phản hồi về ${label}`}>
          {items.slice(0, 30).map((f) => {
            const severity = f.ai_analysis?.severity
            return (
              <li key={f.id}>
                <Link
                  href={`/feedbacks/${f.id}`}
                  className="flex flex-col gap-1.5 rounded-lg border bg-card p-2.5 text-sm transition-colors hover:bg-accent/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  <span className="line-clamp-3 leading-relaxed">“{f.feedback_text}”</span>
                  <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <SentimentIndicator value={f.ai_analysis?.sentiment} />
                    {severity ? (
                      <Badge variant={SEVERITY_TONE[severity] ?? "secondary"}>
                        {SEVERITY_LABEL.vi[severity as Severity] ?? severity}
                      </Badge>
                    ) : null}
                    <span className="ml-auto font-mono">{shortDate(f.occurred_at)}</span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
        {items.length > 30 ? (
          <p className="text-xs text-muted-foreground">
            Đang hiện 30/{items.length} phản hồi mới nhất. Mở tab Bảng để xem toàn bộ.
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}

/** Vì sao biểu đồ chủ đề trống: chưa phân loại gì, hay đã phân loại nhưng mọi
 * mục đều UNCATEGORIZED (chưa có bộ chủ đề lúc chạy). Hai tình huống cần hai
 * việc khác nhau — trước đây cùng hiện một dòng "chưa có chủ đề" (HN-007). */
function TopicsEmpty({ analyzed }: { analyzed: number }) {
  const t = useT().graph
  if (analyzed === 0)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{t.emptyNoneTitle}</EmptyTitle>
          <EmptyDescription>{t.emptyNoneBody}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button size="sm" variant="outline" asChild>
            <Link href="/vault?analyze=1">{t.emptyNoneCta}</Link>
          </Button>
        </EmptyContent>
      </Empty>
    )
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>{t.emptyUncatTitle(analyzed)}</EmptyTitle>
        <EmptyDescription>{t.emptyUncatBody}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="flex-row flex-wrap justify-center">
        <Button size="sm" asChild>
          <Link href="/taxonomy">{t.emptyUncatCta}</Link>
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link href="/vault?reclassify=1">{t.emptyUncatReclassify}</Link>
        </Button>
      </EmptyContent>
    </Empty>
  )
}

function DataGraph({
  initialImportId,
  initialTopic,
  initialRunId,
  askIntent,
}: {
  initialImportId: string | null
  initialTopic: string
  initialRunId: string | null
  /** ?ask=1 từ lộ trình: đưa con trỏ vào ô hỏi. */
  askIntent: boolean
}) {
  const t = useT()
  const { productId } = useProduct()
  const router = useRouter()
  const askRef = useRef<HTMLInputElement>(null)
  const submitting = useRef(false)
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
  const [trendRange, setTrendRange] = useState<TrendRange | null>(null)
  const [selectedTopic, setSelectedTopic] = useInvestigationSession<string>("topic", productId, initialTopic)
  const [question, setQuestion] = useInvestigationSession("question", productId, "")
  const [savedRunId, setRunId] = useInvestigationSession<string | null>("run", productId, null)
  const [runQuestion, setRunQuestion] = useInvestigationSession("run-question", productId, "")
  const runId = initialRunId ?? savedRunId

  const feedbacks = useImportFeedbacks(effectiveScope)
  const items = useMemo(
    () => (feedbacks.data?.items ?? []).filter((f) => Boolean(f.ai_analysis)),
    [feedbacks.data]
  )
  const pendingExcluded = (feedbacks.data?.items.length ?? 0) - items.length
  const dates = items.map((f) => f.occurred_at.slice(0, 10)).sort()

  const words = topTopics(items)
  const tableItems = useMemo(() => {
    if (!trendRange) return items
    return items.filter((item) => {
      const day = feedbackDay(item)
      return day >= trendRange.start && day < trendRange.end
    })
  }, [items, trendRange])
  const matched = useMemo(
    () =>
      selectedTopic
        ? items
            .filter((f) => f.ai_analysis?.topics?.includes(selectedTopic))
            .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at))
        : [],
    [items, selectedTopic]
  )

  const createRun = useCreateAgentRun()

  const askAI = async (text: string = question) => {
    const asked = text.trim()
    if (!productId || asked.length < 3 || submitting.current) return
    submitting.current = true
    setQuestion(asked)
    try {
      const { run_id } = await createRun.mutateAsync({
        product_id: productId,
        question: asked,
      })
      setRunId(run_id)
      setRunQuestion(asked)
      router.replace(`/data-graph?run=${run_id}`, { scroll: false })
      toast.success(t.graph.started)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.graph.startFailed)
    } finally {
      submitting.current = false
    }
  }

  useEffect(() => {
    if (!askIntent) return
    askRef.current?.focus()
    askRef.current?.scrollIntoView({ block: "center" })
    router.replace("/data-graph", { scroll: false })
  }, [askIntent, router])

  // Chưa có gì được phân loại thì AI không có bằng chứng để tìm — chặn sớm và
  // chỉ đường về bước 2 thay vì để cuộc điều tra chạy rồi trả kết luận rỗng.
  // Số liệu ở header chỉ đúng khi cả danh sách file lẫn phản hồi đã về; trước
  // đó `items` rỗng sẽ bị đọc nhầm thành "0 đã phân loại" (QA HN-006).
  const scopeLoading =
    productId == null ||
    importsQuery.isPending ||
    (effectiveScope.length > 0 && feedbacks.isPending)
  const noAnalyzed = !scopeLoading && !feedbacks.isError && items.length === 0
  const canAsk = !scopeLoading && !feedbacks.isError && items.length > 0
  const retryQuestion = runId === savedRunId ? runQuestion : ""

  return (
    <div className="flex flex-col gap-6">
      {/* Đã hỏi và cuộc điều tra đang mở → thẻ điều tra (có sẵn phần tạo
          hành động sau khi duyệt) là việc chính, không lặp lời mời. */}
      <NextStepBar
        hideKinds={runId ? ["ask", "open-actions", "generate-actions"] : []}
      />
      <PageHeader
        title={t.nav.items.dataGraph}
        description={
          scopeLoading
            ? t.graph.scopeLoading
            : effectiveScope.length > 0
              ? scopeLine(
                  effectiveScope.length,
                  dates[0] ?? "—",
                  dates.at(-1) ?? "—",
                  items.length,
                  pendingExcluded
                )
              : t.graph.scopeEmpty
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
            setTrendRange(null)
          }}
        />

        <div className="flex min-w-0 flex-col gap-4">
          {/* Cuộc điều tra đang mở (đang chạy / chờ duyệt) là việc chính của
              màn — đặt trên ô hỏi để không phải cuộn mới thấy phần duyệt. */}
          {runId ? (
            <InvestigationCard
              key={runId}
              runId={runId}
              question={retryQuestion || null}
              onRetry={retryQuestion ? () => void askAI(retryQuestion) : undefined}
            />
          ) : null}
          <Card>
            <CardHeader>
              <CardTitle>{t.graph.askTitle}</CardTitle>
              <CardDescription>{t.graph.askBody}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                <InputGroup className="min-w-44 flex-1">
                  <InputGroupInput
                    ref={askRef}
                    placeholder={t.graph.placeholder}
                    value={question}
                    disabled={noAnalyzed}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.nativeEvent.isComposing && !e.repeat) {
                        e.preventDefault()
                        if (canAsk) void askAI()
                      }
                    }}
                  />
                </InputGroup>
                <Button
                  onClick={() => void askAI()}
                  disabled={
                    !canAsk || question.trim().length < 3 || createRun.isPending
                  }
                >
                  {createRun.isPending ? (
                    <Spinner data-icon="inline-start" />
                  ) : (
                    <Send data-icon="inline-start" />
                  )}
                  {t.graph.ask}
                </Button>
              </div>
              {noAnalyzed ? (
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <span>{t.graph.noData}</span>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/vault">{t.graph.goClassify}</Link>
                  </Button>
                </div>
              ) : canAsk ? (
                <div
                  className="flex flex-wrap gap-2"
                  role="group"
                  aria-label={t.graph.suggestionsLabel}
                >
                  {t.graph.suggestions.map((suggestion) => (
                    <Button
                      key={suggestion}
                      size="sm"
                      variant="outline"
                      disabled={createRun.isPending}
                      onClick={() => {
                        setQuestion(suggestion)
                        askRef.current?.focus()
                      }}
                      className="h-auto min-h-8 max-w-full whitespace-normal text-left"
                    >
                      <Sparkles data-icon="inline-start" />
                      {suggestion}
                    </Button>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div
            className={cn(
              "grid min-w-0 items-start gap-4",
              selectedTopic && "xl:grid-cols-[minmax(0,1fr)_minmax(18rem,22rem)]"
            )}
          >
          <Tabs value={tab} onValueChange={setTab} className="min-w-0">
            <TabsList className="max-w-full flex-wrap group-data-horizontal/tabs:h-auto">
              <TabsTrigger value="cloud">Đám mây chủ đề</TabsTrigger>
              <TabsTrigger value="trends">{t.graph.trends.tab}</TabsTrigger>
              <TabsTrigger value="topics">Chủ đề</TabsTrigger>
              <TabsTrigger value="table">Bảng</TabsTrigger>
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
                        selected={selectedTopic}
                        onSelect={setSelectedTopic}
                      />
                      <p className="pb-4 text-center text-xs text-muted-foreground">
                        Cỡ chữ = số phản hồi nhắc tới chủ đề. Bấm một chủ đề để đọc phản hồi gốc.
                      </p>
                    </>
                  ) : (
                    <TopicsEmpty analyzed={items.length} />
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="trends">
              {scopeLoading ? (
                <Card><CardContent className="items-center p-8"><Spinner /></CardContent></Card>
              ) : feedbacks.isError ? (
                <Card>
                  <CardContent className="items-start">
                    <p className="text-sm text-muted-foreground">{t.graph.trends.loadFailed}</p>
                    <Button size="sm" variant="outline" onClick={() => void feedbacks.refetch()}>{t.graph.trends.retry}</Button>
                  </CardContent>
                </Card>
              ) : (
                <FeedbackTrends
                  items={items}
                  partial={feedbacks.data?.partial ?? false}
                  onViewFeedback={(range) => {
                    setTrendRange(range)
                    setTab("table")
                  }}
                />
              )}
            </TabsContent>
            <TabsContent value="topics">
              <Card>
                <CardContent className="p-0">
                  {feedbacks.isPending ? (
                    <div className="p-8 text-center">
                      <Spinner />
                    </div>
                  ) : words.length === 0 ? (
                    <TopicsEmpty analyzed={items.length} />
                  ) : (
                  <ul className="flex flex-col gap-3 p-6">
                      {words.map(({ topic, count }) => (
                        <li key={topic} className="flex items-center gap-3">
                          <button
                            aria-pressed={topic === selectedTopic}
                            className={cn(
                              "w-32 truncate text-left text-sm font-medium hover:text-signal",
                              topic === selectedTopic && "text-signal underline underline-offset-4"
                            )}
                            onClick={() => setSelectedTopic(topic === selectedTopic ? "" : topic)}
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
                  </ul>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="table">
              {trendRange ? (
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card px-3 py-2">
                  <p className="text-sm">{trendRange.label} · {t.graph.trends.count(tableItems.length)}</p>
                  <Button size="sm" variant="ghost" onClick={() => setTrendRange(null)}>{t.graph.trends.clear}</Button>
                </div>
              ) : null}
              {scopeLoading ? (
                <Card>
                  <CardContent className="flex justify-center p-8">
                    <Spinner />
                  </CardContent>
                </Card>
              ) : tableItems.length ? (
                <ScopeTable key={trendRange?.start} items={tableItems} topicLabel={topicLabel} />
              ) : trendRange ? (
                <Card><CardContent>{t.graph.trends.emptyTitle}</CardContent></Card>
              ) : (
                <Card>
                  <CardContent className="p-0">
                    <TopicsEmpty analyzed={0} />
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>

          {selectedTopic ? (
            <TopicPanel
              topic={selectedTopic}
              label={topicLabel(selectedTopic)}
              items={matched}
              onClear={() => setSelectedTopic("")}
              onAsk={() => {
                setQuestion(`Vì sao người dùng phản hồi về “${topicLabel(selectedTopic)}”?`)
                askRef.current?.focus()
                askRef.current?.scrollIntoView({ block: "center", behavior: "smooth" })
              }}
            />
          ) : null}
          </div>

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
      askIntent={params.get("ask") === "1"}
    />
  )
}

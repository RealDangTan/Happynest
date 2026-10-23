"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import type {
  ColumnFiltersState,
  RowSelectionState,
  SortingState,
} from "@tanstack/react-table"
import {
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  useLegacyTable,
  type LegacyColumnDef,
} from "@tanstack/react-table/legacy"
import {
  Ban,
  FileSpreadsheet,
  Pencil,
  Play,
  Trash2,
  Unlock,
  X,
} from "lucide-react"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  DataTableToolbar,
} from "@/components/data-table"
import { Textarea } from "@/components/ui/textarea"
import { apiFetch } from "@/lib/api"
import type {
  Feedback,
  FeedbackListResponse,
  ImportRecord,
  RunProgress,
} from "@/lib/types"
import {
  useBulkDeleteFeedbacks,
  useDeleteFeedback,
  useDeleteImport,
  useFeedbacks,
  useUpdateFeedback,
} from "@/hooks/use-feedbacks"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { useStoredState } from "@/hooks/use-stored-state"
import {
  useAnalysisPreview,
  useCancelRun,
  useRunProgress,
  useTriggerRun,
} from "@/hooks/use-analysis"
import { useReEnrichUncategorized, useTaxonomy } from "@/hooks/use-taxonomy"
import {
  useFeedbackDetail,
  useSimilarFeedbacks,
} from "@/hooks/use-feedback-detail"
import { PageHeader } from "@/components/page-header"
import { useProduct } from "@/hooks/use-product"
import { shortDate, topicLabeler } from "@/lib/graph"
import {
  multiSelectFilterFn,
  sortingToServerSort,
} from "@/lib/table-sorts"

type Scope =
  | { mode: "selected"; import_id: string; feedback_ids: string[] }
  | { mode: "batch"; import_id: string }

function ImportRowButton({
  item,
  active,
  onSelect,
  onDelete,
}: {
  item: ImportRecord
  active: boolean
  onSelect: () => void
  onDelete?: () => void
}) {
  return (
    <div
      className={`group flex w-full items-center rounded-md pr-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active ? "bg-accent font-medium" : "hover:bg-accent/60"
      }`}
    >
      <button
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left outline-none"
      >
        {active ? (
          <span aria-hidden>›</span>
        ) : (
          <span className="w-2" aria-hidden />
        )}
        <FileSpreadsheet className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="min-w-0 flex-1 truncate">
          {item.original_filename ?? item.id.slice(0, 8)}
        </span>
        {item.status === "imported" ? null : (
          <Badge
            variant={item.status === "failed" ? "destructive" : "secondary"}
          >
            {item.status === "mapping_review" || item.status === "profile_ready"
              ? "mapping"
              : item.status}
          </Badge>
        )}
      </button>
      {onDelete ? (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity outline-none group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Delete import"
          title="Delete import"
        >
          <Trash2 className="size-3.5" />
        </button>
      ) : null}
    </div>
  )
}

const SEVERITIES = ["low", "medium", "high", "critical"] as const
const SENTIMENTS = ["positive", "neutral", "negative", "mixed"] as const

function FeedbackEditDialog({
  feedback,
  open,
  onOpenChange,
}: {
  feedback: Feedback | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const update = useUpdateFeedback()
  // State khởi tạo từ prop; mount site dùng key={feedback.id} để re-seed form
  // mỗi lần mở feedback khác — không cần effect ghi đè state.
  const [text, setText] = useState(feedback?.feedback_text ?? "")
  const [source, setSource] = useState(feedback?.source ?? "")
  const [occurredAt, setOccurredAt] = useState(
    feedback?.occurred_at ? feedback.occurred_at.slice(0, 16) : ""
  )
  const [severity, setSeverity] = useState(
    feedback?.ai_analysis?.severity ?? ""
  )
  const [sentiment, setSentiment] = useState(
    feedback?.ai_analysis?.sentiment ?? ""
  )
  const [topics, setTopics] = useState(
    (feedback?.ai_analysis?.topics ?? []).join(", ")
  )

  if (!feedback) return null
  const analysis = feedback.ai_analysis

  const save = () => {
    const body: Parameters<typeof update.mutate>[0]["body"] = {}
    if (text.trim() && text !== feedback.feedback_text)
      body.feedback_text = text.trim()
    if (source.trim() && source !== feedback.source) body.source = source.trim()
    if (occurredAt && occurredAt !== feedback.occurred_at.slice(0, 16))
      body.occurred_at = new Date(occurredAt).toISOString()
    const ai: NonNullable<
      Parameters<typeof update.mutate>[0]["body"]["ai_analysis"]
    > = {}
    if (severity && severity !== (analysis?.severity ?? ""))
      ai.severity = severity
    if (sentiment && sentiment !== (analysis?.sentiment ?? ""))
      ai.sentiment = sentiment
    const topicList = topics
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
    if (topics !== (analysis?.topics ?? []).join(", ")) ai.topics = topicList
    if (Object.keys(ai).length > 0) body.ai_analysis = ai
    if (Object.keys(body).length === 0) {
      onOpenChange(false)
      return
    }

    update.mutate(
      { id: feedback.id, body },
      {
        onSuccess: () => {
          toast.success(
            "Đã lưu thay đổi. Text mới sẽ được sanitize lại tự động."
          )
          onOpenChange(false)
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Không lưu được thay đổi."
          ),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Edit feedback{" "}
            <span className="font-mono text-sm text-signal">
              F-{feedback.id.slice(0, 8)}
            </span>
          </DialogTitle>
          <DialogDescription>
            Text sửa sẽ chạy lại bộ lọc PII; vector embedding cũ bị gỡ để phân
            tích lần sau tính lại đúng.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="fb-edit-text">Nội dung</FieldLabel>
            <Textarea
              id="fb-edit-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field>
              <FieldLabel htmlFor="fb-edit-source">Nguồn</FieldLabel>
              <Input
                id="fb-edit-source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="fb-edit-occurred">Occurred at</FieldLabel>
              <Input
                id="fb-edit-occurred"
                type="datetime-local"
                value={occurredAt}
                onChange={(e) => setOccurredAt(e.target.value)}
              />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field>
              <FieldLabel>Severity</FieldLabel>
              <Select value={severity} onValueChange={setSeverity}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITIES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Sentiment</FieldLabel>
              <Select value={sentiment} onValueChange={setSentiment}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {SENTIMENTS.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="fb-edit-topics">Topics</FieldLabel>
              <Input
                id="fb-edit-topics"
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                placeholder="cách nhau bởi dấu phẩy"
              />
            </Field>
          </div>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={update.isPending || !text.trim()}>
            {update.isPending ? <Spinner data-icon="inline-start" /> : null}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function FeedbackDetailDrawer({
  feedbackId,
  labelTopic,
  onClose,
  onEdit,
  onDelete,
}: {
  feedbackId: string | null
  labelTopic: (topic: string) => string
  onClose: () => void
  onEdit: (item: Feedback) => void
  onDelete: (id: string) => void
}) {
  const detail = useFeedbackDetail(feedbackId ?? "")
  const similar = useSimilarFeedbacks(feedbackId ?? "")
  const router = useRouter()
  const item = detail.data
  const analysis = item?.ai_analysis ?? null

  return (
    <Sheet
      open={feedbackId != null}
      onOpenChange={(open) => !open && onClose()}
    >
      <SheetContent className="overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <span className="font-mono text-signal">
              F-{item ? item.id.slice(0, 8) : "…"}
            </span>
          </SheetTitle>
          <SheetDescription>Feedback detail</SheetDescription>
        </SheetHeader>
        {item ? (
          <div className="flex flex-col gap-6 px-4 pb-8">
            <p className="text-sm leading-relaxed">
              {item.feedback_text ?? "—"}
            </p>
            <Card size="sm">
              <CardContent className="gap-2 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Import</span>
                  <span className="font-mono text-xs">
                    {item.import_id ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Occurred</span>
                  <span className="font-mono text-xs">
                    {shortDate(item.occurred_at)}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="shrink-0 text-muted-foreground">Topic</span>
                  <span className="flex min-w-0 flex-wrap justify-end gap-1">
                    {analysis?.uncategorized ? (
                      <Badge variant="outline">UNCATEGORIZED</Badge>
                    ) : null}
                    {(analysis?.topics ?? []).length > 0
                      ? (analysis?.topics ?? []).map((t) => (
                          <code
                            key={t}
                            title={t}
                            className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                          >
                            {labelTopic(t)}
                          </code>
                        ))
                      : analysis?.uncategorized
                        ? null
                        : "—"}
                  </span>
                </div>
                {(analysis?.emotions ?? []).length > 0 || analysis?.intent ? (
                  <>
                    <div className="flex justify-between gap-4">
                      <span className="shrink-0 text-muted-foreground">
                        Emotions
                      </span>
                      <span className="flex flex-wrap justify-end gap-1">
                        {(analysis?.emotions ?? []).length > 0
                          ? analysis!.emotions!.map((e) => (
                              <Badge key={e} variant="secondary">
                                {e}
                              </Badge>
                            ))
                          : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-muted-foreground">Intent</span>
                      <span>{analysis?.intent ?? "—"}</span>
                    </div>
                  </>
                ) : null}
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Sentiment</span>
                  <SentimentIndicator value={analysis?.sentiment} />
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Analysis</span>
                  <span>
                    <Badge variant={analysis ? "secondary" : "outline"}>
                      {analysis ? "Ready" : "Pending"}
                    </Badge>
                  </span>
                </div>
              </CardContent>
            </Card>

            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  router.push(
                    `/data-graph?import=${item.import_id ?? ""}${
                      analysis?.topics?.[0]
                        ? `&topic=${encodeURIComponent(analysis.topics[0])}`
                        : ""
                    }`
                  )
                }
              >
                Explore this topic
              </Button>
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onEdit(item)}
                >
                  <Pencil data-icon="inline-start" />
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => onDelete(item.id)}
                >
                  <Trash2 data-icon="inline-start" />
                  Delete
                </Button>
              </>
            </div>

            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">Similar feedback</h3>
              {similar.isPending ? (
                <Spinner />
              ) : similar.data && similar.data.length ? (
                <div className="flex flex-col gap-2">
                  {similar.data.map((s) => (
                    <Card key={s.id} size="sm">
                      <CardContent className="gap-1 text-sm">
                        <p className="line-clamp-2">{s.snippet ?? "—"}</p>
                        <p className="font-mono text-xs text-signal">
                          F-{s.id.slice(0, 8)} · similarity {s.score.toFixed(2)}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Similarity needs analysis first — this item has no embedding
                  yet.
                </p>
              )}
            </section>

            <Button variant="ghost" size="sm" onClick={onClose}>
              Back to originating view
            </Button>
          </div>
        ) : (
          <div className="px-4">
            <Spinner />
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

function RunningAnalysisCard({
  runId,
  onDismiss,
}: {
  runId: string
  onDismiss: () => void
}) {
  const run = useRunProgress(runId)
  const cancel = useCancelRun()
  const qc = useQueryClient()
  const data: RunProgress | undefined = run.data
  const pct = data?.total_count
    ? Math.round((data.processed_count / data.total_count) * 100)
    : 0
  // Run xong tự tải lại danh sách feedback — không bắt user bấm "Refresh
  // results"; theo dõi status TRƯỚC đó để chỉ fire đúng lúc chuyển pha.
  const prevStatus = useRef<string | null>(null)
  useEffect(() => {
    if (!data) return
    if (prevStatus.current === "running" && data.status !== "running") {
      void qc.invalidateQueries({ queryKey: ["feedbacks"] })
      if (data.status === "completed") {
        toast.success("Phân tích hoàn tất — danh sách đã cập nhật.")
      } else if (data.status === "failed") {
        toast.error("Run phân tích lỗi — xem tóm tắt trong thẻ tiến trình.")
      }
    }
    prevStatus.current = data.status
  }, [data, qc])

  if (!data) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Analysis{" "}
          <span className="font-mono text-signal">{runId.slice(0, 8)}</span>
        </CardTitle>
        <CardDescription>Processing selected feedback</CardDescription>
        <CardAction>
          <Badge variant={data.status === "running" ? "secondary" : "outline"}>
            {data.status}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="gap-2">
        <Progress value={pct} />
        <p className="font-mono text-sm">
          {data.processed_count} / {data.total_count}
        </p>
        <p className="text-xs text-muted-foreground">
          You can leave this screen. Reopen from Current tasks.
        </p>
      </CardContent>
      <CardFooter>
        {data.status === "running" ? (
          <Button
            size="sm"
            variant="outline"
            disabled={cancel.isPending || Boolean(data.cancel_requested_at)}
            onClick={() =>
              cancel.mutate(runId, {
                onSuccess: () => {
                  toast.success(
                    "Stop requested — it applies after the current item."
                  )
                  void qc.invalidateQueries({ queryKey: ["feedbacks"] })
                },
              })
            }
          >
            <Ban data-icon="inline-start" />
            {data.cancel_requested_at ? "Stopping…" : "Stop analysis"}
          </Button>
        ) : (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Đóng thẻ tiến trình
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}

function Vault({ initialImportId }: { initialImportId: string | null }) {
  const { product, productId } = useProduct()
  const router = useRouter()
  const qc = useQueryClient()
  // The ?import= URL param is the single source of truth for the active file.
  const activeImportId = initialImportId
  const setActiveImportId = (id: string | null) => {
    router.replace(id ? `/vault?import=${id}` : "/vault", { scroll: false })
  }
  // Table state: phân trang/sort/search chạy server-side (manual mode) —
  // search TRÊN TOÀN BỘ tập dữ liệu, không phải từng trang như trước đây.
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useStoredState<number>(
    "vault.pageSize",
    20,
    (raw) => {
      const n = Number(JSON.parse(raw))
      return [10, 20, 50, 100].includes(n) ? n : null
    },
  )
  const [sorting, setSorting] = useState<SortingState>([
    { id: "occurred_at", desc: true },
  ])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [qInput, setQInput] = useState("")
  const debouncedQ = useDebouncedValue(qInput, 300)
  const [topic, setTopic] = useState<string>("")
  const [analysisState, setAnalysisState] = useState<string>("")
  const [detailId, setDetailId] = useState<string | null>(null)
  const [receiptScope, setReceiptScope] = useState<Scope | null>(null)
  const [startedRunId, setStartedRunId] = useState<string | null>(null)

  // Selection qua TanStack (rowSelection) nhưng đọc thành Set cho logic cũ.
  const selected = useMemo(
    () =>
      new Set(
        Object.entries(rowSelection)
          .filter(([, v]) => v)
          .map(([k]) => k),
      ),
    [rowSelection],
  )
  function clearSelection() {
    setRowSelection({})
  }

  const deleteFeedback = useDeleteFeedback()
  const bulkDelete = useBulkDeleteFeedbacks()
  const deleteImport = useDeleteImport()
  const [editing, setEditing] = useState<Feedback | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmBulk, setConfirmBulk] = useState(false)
  const [confirmImport, setConfirmImport] = useState<ImportRecord | null>(null)

  const importsQuery = useQuery({
    queryKey: ["imports", "vault", productId],
    queryFn: () =>
      apiFetch<{ items: ImportRecord[] }>(
        `/api/imports?limit=50&product_id=${productId}&status=imported`
      ),
    enabled: productId != null,
    staleTime: 30_000,
  })
  const imports = importsQuery.data?.items ?? []

  // Taxonomy của product: nhãn hiển thị tiếng Việt cho slug trong
  // ai_analysis.topics + danh sách chọn của filter Topic (thay bộ hardcode).
  const taxonomy = useTaxonomy(productId)
  const labelTopic = useMemo(
    () => topicLabeler(taxonomy.data?.items ?? []),
    [taxonomy.data]
  )
  const topicOptions = useMemo(() => {
    const seen = new Set<string>()
    return (taxonomy.data?.items ?? [])
      .filter((n) => {
        const value = n.slug ?? n.name
        if (!value || seen.has(value)) return false
        seen.add(value)
        return true
      })
      .sort((a, b) => (a.name_vi ?? a.name).localeCompare(b.name_vi ?? b.name, "vi"))
  }, [taxonomy.data])

  const filters = {
    page,
    pageSize,
    importId: activeImportId ?? undefined,
    analysisState: (analysisState || undefined) as
      | "pending"
      | "completed"
      | "uncategorized"
      | undefined,
    sentiment:
      (columnFilters.find((f) => f.id === "sentiment")?.value as string[]) ??
      undefined,
    topic: topic || undefined,
    q: debouncedQ.trim() || undefined,
    sort: sortingToServerSort(sorting),
  }
  const feedbacks = useFeedbacks(filters)
  const rows = useMemo(() => feedbacks.data?.items ?? [], [feedbacks.data])

  const pendingCount = useQuery({
    queryKey: ["feedbacks", "pending-count", activeImportId],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=pending${
          activeImportId ? `&import_id=${activeImportId}` : ""
        }`
      ),
    staleTime: 15_000,
  })

  // Đếm rows ĐÃ analyzed nhưng mang nhãn UNCATEGORIZED theo taxonomy cũ —
  // hết pending mà vẫn còn UNCATEGORIZED = taxonomy vừa đổi, cần mở khoá
  // re-enrich (vòng taxonomy evolution, plan 32).
  const uncategorizedCount = useQuery({
    queryKey: ["feedbacks", "uncategorized-count", productId],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=uncategorized&product_id=${productId}`
      ),
    enabled: productId != null,
    staleTime: 15_000,
  })
  const reEnrich = useReEnrichUncategorized()
  const unlockUncategorized = () => {
    if (!productId) return
    reEnrich.mutate(
      { product_id: productId },
      {
        onSuccess: (res) => {
          toast.success(
            res.released > 0
              ? `Đã mở khoá ${res.released} phản hồi — bấm Analyze pending items để chạy lại theo nhãn mới.`
              : "Không có phản hồi nào cần mở khoá."
          )
          void qc.invalidateQueries({ queryKey: ["feedbacks"] })
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Không mở khoá được phản hồi."
          ),
      }
    )
  }

  const preview = useAnalysisPreview()
  const trigger = useTriggerRun()

  // A running scoped analysis for this import (e.g. reopened from Current tasks).
  // Poll 30s: chỉ để phát hiện run đang chạy khi mở lại trang — mỗi request tốn
  // ~1s RTT tới DB xa, poll 6s gây tải nền liên tục không cần thiết.
  const runningRun = useQuery({
    queryKey: ["analysis", "runs", "vault-active", activeImportId],
    queryFn: () =>
      apiFetch<{ items: RunProgress[] }>(
        `/api/analysis/runs?limit=10&status=running`
      ),
    refetchInterval: 30_000,
  })
  const activeRunId =
    startedRunId ??
    runningRun.data?.items.find(
      (r) => r.import_id && r.import_id === activeImportId
    )?.id ??
    null

  const selectedPending = useMemo(() => {
    return [...selected].filter((id) => {
      const row = rows.find((r) => r.id === id)
      return row && !row.ai_analysis
    })
  }, [selected, rows])

  const selectedReady = selected.size - selectedPending.length

  const startAnalysis = () => {
    if (!receiptScope || !preview.data) return
    trigger.mutate(
      { scope: receiptScope, confirmedItemCount: preview.data.selected_count },
      {
        onSuccess: ({ run_id }) => {
          setStartedRunId(run_id)
          setReceiptScope(null)
          preview.reset()
          void qc.invalidateQueries({ queryKey: ["feedbacks"] })
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Could not start analysis"
          ),
      }
    )
  }

  const openReceipt = async () => {
    if (!productId) return
    const scope: Scope =
      selectedPending.length > 0 && activeImportId
        ? {
            mode: "selected",
            import_id: activeImportId,
            feedback_ids: selectedPending,
          }
        : activeImportId
          ? { mode: "batch", import_id: activeImportId }
          : { mode: "batch", import_id: imports[0]?.id ?? "" }
    if (!scope.import_id) {
      toast.error("Choose an import first.")
      return
    }
    try {
      await preview.mutateAsync(scope)
      setReceiptScope(scope)
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Could not preview analysis"
      )
    }
  }

  const exploreSelected = () => {
    if (activeImportId) {
      sessionStorage.setItem(
        "vault.explore",
        JSON.stringify({ importId: activeImportId, ids: [...selected] })
      )
      router.push(`/data-graph?import=${activeImportId}`)
    }
  }

  const hasActiveFilters =
    columnFilters.length > 0 || debouncedQ.trim() !== "" || topic !== "" || analysisState !== ""
  function clearAllFilters() {
    setQInput("")
    setColumnFilters([])
    setTopic("")
    setAnalysisState("")
    setSorting([{ id: "occurred_at", desc: true }])
    setPage(1)
  }

  const pagination = { pageIndex: page - 1, pageSize }
  const total = feedbacks.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / pageSize))

  // ── Table instance (manual mode: server sort/search/filter/pagination) ──
  const columns = useMemo<LegacyColumnDef<Feedback>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        enableHiding: false,
        meta: { thClassName: "w-10", tdClassName: "w-10" },
        header: ({ table }) => (
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected()
                ? true
                : table.getIsSomePageRowsSelected()
                  ? "indeterminate"
                  : false
            }
            onCheckedChange={(value) =>
              table.toggleAllPageRowsSelected(!!value)
            }
            aria-label="Select all rows on this page"
          />
        ),
        cell: ({ row }) => (
          <div
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            <Checkbox
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(!!value)}
              aria-label="Select feedback"
            />
          </div>
        ),
      },
      {
        id: "content",
        enableSorting: false,
        enableHiding: false,
        meta: { label: "Feedback", thClassName: "w-[38%]" },
        header: "Feedback",
        cell: ({ row }) => (
          <>
            <span className="line-clamp-2 block max-w-md text-sm">
              {row.original.feedback_text ?? "—"}
            </span>
            {row.original.pii_detected ? (
              <Badge variant="outline" className="ml-2">
                PII masked
              </Badge>
            ) : null}
          </>
        ),
      },
      {
        id: "source",
        accessorFn: (f: Feedback) => f.source,
        meta: { label: "Source" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Source" />
        ),
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.source}
          </span>
        ),
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
      {
        id: "severity",
        accessorFn: (f: Feedback) => f.ai_analysis?.severity ?? "",
        filterFn: multiSelectFilterFn,
        sortDescFirst: true,
        meta: { label: "Severity" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Severity" />
        ),
        cell: ({ row }) => {
          const severity = row.original.ai_analysis?.severity
          if (!severity) return <span className="text-muted-foreground">—</span>
          return (
            <Badge
              variant={
                severity === "critical" || severity === "high"
                  ? "destructive"
                  : "secondary"
              }
            >
              {severity}
            </Badge>
          )
        },
      },
      {
        id: "topics",
        enableSorting: false,
        meta: { label: "Topic" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Topic" />
        ),
        cell: ({ row }) => {
          if (row.original.ai_analysis?.uncategorized)
            return <Badge variant="outline">UNCATEGORIZED</Badge>
          const first = row.original.ai_analysis?.topics?.[0]
          return first ? (
            <span title={first} className="block max-w-48 truncate text-sm">
              {labelTopic(first)}
            </span>
          ) : (
            "—"
          )
        },
      },
      {
        id: "state",
        enableSorting: false,
        enableHiding: false,
        meta: { label: "State" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="State" />
        ),
        cell: ({ row }) => {
          const ready = Boolean(row.original.ai_analysis)
          return (
            <Badge variant={ready ? "secondary" : "outline"}>
              {ready ? "Ready" : "Pending"}
            </Badge>
          )
        },
      },
    ],
    [labelTopic],
  )

  const table = useLegacyTable({
    data: rows,
    columns,
    getRowId: (f) => f.id,
    manualPagination: true,
    pageCount,
    manualSorting: true,
    manualFiltering: true,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    state: { sorting, columnFilters, rowSelection, pagination },
    onSortingChange: (updater) => {
      setSorting((old) =>
        typeof updater === "function" ? updater(old) : updater,
      )
      setPage(1)
    },
    onColumnFiltersChange: (updater) => {
      setColumnFilters((old) =>
        typeof updater === "function" ? updater(old) : updater,
      )
      setPage(1)
    },
    onRowSelectionChange: setRowSelection,
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater(pagination) : updater
      if (next.pageSize !== pageSize) {
        setPageSize(next.pageSize)
        setPage(1)
      } else if (next.pageIndex !== page - 1) {
        setPage(next.pageIndex + 1)
      }
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={product?.name ?? "Feedback Vault"}
        documentTitle="Feedback Vault"
        description="Duyệt từng phản hồi, gắn nhãn hàng loạt, và chạy phân loại có kiểm soát."
        actions={
          <Button asChild>
            <Link href="/importer">Import CSV</Link>
          </Button>
        }
      />

      <div className="grid min-w-0 gap-6 lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-2">
          <h2 className="px-2 pb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            Files
          </h2>
          <ImportRowButton
            item={
              {
                id: "all",
                status: "imported",
                original_filename: "All imports",
              } as ImportRecord
            }
            active={!activeImportId}
            onSelect={() => {
              setActiveImportId(null)
              clearSelection()
              setPage(1)
            }}
          />
          {imports.map((item) => (
            <ImportRowButton
              key={item.id}
              item={item}
              active={activeImportId === item.id}
              onSelect={() => {
                setActiveImportId(item.id)
                clearSelection()
                setPage(1)
              }}
              onDelete={() => setConfirmImport(item)}
            />
          ))}
          {imports.length === 0 ? (
            <p className="px-2 text-sm text-muted-foreground">
              No imported files yet.
            </p>
          ) : null}
        </aside>

        <div className="flex min-w-0 flex-col gap-4">
          <DataTableToolbar
            table={table}
            search={{
              value: qInput,
              onChange: (v) => {
                setQInput(v)
                setPage(1)
              },
            }}
            filters={[
              {
                columnId: "sentiment",
                title: "Sentiment",
                options: [
                  { value: "negative", label: "Negative" },
                  { value: "neutral", label: "Neutral" },
                  { value: "positive", label: "Positive" },
                  { value: "mixed", label: "Mixed" },
                ],
              },
            ]}
          >
            <Select
              value={topic}
              onValueChange={(v) => {
                setTopic(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger size="sm" className="w-40">
                <SelectValue placeholder="Topic" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Topic: any</SelectItem>
                {topicOptions.map((n) => (
                  <SelectItem key={n.id} value={n.slug ?? n.name}>
                    {n.name_vi ?? n.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={analysisState}
              onValueChange={(v) => {
                setAnalysisState(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger size="sm" className="w-40">
                <SelectValue placeholder="Analysis state" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Analysis: any</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="completed">Ready</SelectItem>
                <SelectItem value="uncategorized">UNCATEGORIZED</SelectItem>
              </SelectContent>
            </Select>
          </DataTableToolbar>

          {activeRunId ? (
            <RunningAnalysisCard
              runId={activeRunId}
              onDismiss={() => setStartedRunId(null)}
            />
          ) : null}

          {/* Taxonomy vừa đổi nhưng nhãn cũ còn treo: gợi ý mở khoá ngay tại
              vault thay vì bắt user quay lại trang Taxonomy (2026-10-23). */}
          {(pendingCount.data?.total ?? 0) === 0 &&
          (uncategorizedCount.data?.total ?? 0) > 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-xl border bg-secondary/40 px-4 py-3 text-sm">
              <p className="flex min-w-0 items-center gap-2 text-muted-foreground">
                <Unlock className="size-4 shrink-0" aria-hidden />
                <span>
                  <strong className="font-medium text-foreground">
                    {uncategorizedCount.data?.total} phản hồi
                  </strong>{" "}
                  đã phân loại nhưng đang mang nhãn UNCATEGORIZED theo bộ nhãn
                  cũ. Mở khoá để chạy lại theo taxonomy hiện tại.
                </span>
              </p>
              <Button
                size="sm"
                variant="outline"
                disabled={reEnrich.isPending}
                onClick={unlockUncategorized}
              >
                {reEnrich.isPending ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <Unlock data-icon="inline-start" />
                )}
                Mở khoá để phân tích lại
              </Button>
            </div>
          ) : null}

          <Card className="py-0">
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b px-(--card-spacing) py-(--card-spacing)">
              <div className="text-sm text-muted-foreground">
                {selected.size > 0 ? (
                  <>
                    {selected.size} selected · {selectedPending.length} pending,{" "}
                    {selectedReady} ready
                    <Button
                      size="sm"
                      variant="ghost"
                      className="ml-2"
                      onClick={clearSelection}
                    >
                      <X data-icon="inline-start" />
                      Clear selection
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => setConfirmBulk(true)}
                    >
                      <Trash2 data-icon="inline-start" />
                      Delete selected
                    </Button>
                  </>
                ) : (
                  <>
                    {pendingCount.data?.total ?? 0} pending in this scope ·
                    batch caps at 100
                  </>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  onClick={() => void openReceipt()}
                  disabled={
                    preview.isPending ||
                    (selectedPending.length === 0 &&
                      !activeImportId &&
                      (pendingCount.data?.total ?? 0) === 0)
                  }
                >
                  {preview.isPending ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  Analyze pending items
                </Button>
                {selected.size > 0 && selectedPending.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    {selectedReady} ready selected will be excluded from
                    analysis.
                  </p>
                ) : null}
                <Button
                  variant="outline"
                  disabled={selectedReady === 0 && !activeImportId}
                  onClick={exploreSelected}
                >
                  Explore selected
                </Button>
              </div>
            </div>
            <CardContent className="p-0">
              <DataTable
                table={table}
                isLoading={feedbacks.isFetching && !feedbacks.data}
                maxHeightClass="max-h-[65vh]"
                onRowClick={(row) => setDetailId(row.id)}
                emptyContent={
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>
                        {hasActiveFilters
                          ? "Nothing matches these filters"
                          : "No feedback in this workspace yet"}
                      </EmptyTitle>
                      <EmptyDescription>
                        {hasActiveFilters
                          ? "Clear filters to return to the complete result set."
                          : "Import a CSV from the LISTEN stage to get started."}
                      </EmptyDescription>
                    </EmptyHeader>
                    {hasActiveFilters ? (
                      <EmptyContent>
                        <Button size="sm" variant="outline" onClick={clearAllFilters}>
                          Clear filters
                        </Button>
                      </EmptyContent>
                    ) : null}
                  </Empty>
                }
              />
            </CardContent>
            <CardFooter className="flex-col items-stretch border-t">
              <DataTablePagination table={table} />
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* L05 — analysis receipt */}
      <AlertDialog
        open={receiptScope != null}
        onOpenChange={(open) => {
          if (!open) {
            setReceiptScope(null)
            preview.reset()
          }
        }}
      >
        <AlertDialogContent className="sm:max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Review analysis</AlertDialogTitle>
            <AlertDialogDescription>
              Product: {product?.name ?? "—"} · Import:{" "}
              {imports.find((i) => i.id === receiptScope?.import_id)
                ?.original_filename ?? receiptScope?.import_id.slice(0, 8)}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {preview.data ? (
            <div className="grid grid-cols-2 gap-2 rounded-lg bg-secondary/50 p-3 text-sm sm:grid-cols-3">
              <span>
                <strong className="font-mono">
                  {preview.data.selected_count}
                </strong>
                <br />
                in scope
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.logical_classify_requests}
                </strong>
                <br />
                classify calls
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.logical_embedding_requests}
                </strong>
                <br />
                embed calls
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.max_provider_attempts}
                </strong>
                <br />
                max attempts
              </span>
              <span>
                <strong className="font-mono">
                  ~{preview.data.estimated_input_tokens}
                </strong>
                <br />
                input tokens
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.remaining_count}
                </strong>
                <br />
                remaining
              </span>
            </div>
          ) : (
            <Spinner />
          )}
          <p className="text-xs text-muted-foreground">
            Estimate available before starting. If the selection changed since
            this preview, the run is rejected and you review again.
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Back</AlertDialogCancel>
            <AlertDialogAction
              disabled={!preview.data || trigger.isPending}
              onClick={(e) => {
                e.preventDefault()
                startAnalysis()
              }}
            >
              <Play data-icon="inline-start" />
              Start analysis
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <FeedbackEditDialog
        key={editing?.id ?? "none"}
        feedback={editing}
        open={editing != null}
        onOpenChange={(open) => !open && setEditing(null)}
      />

      {/* confirm delete single feedback (from detail drawer) */}
      <AlertDialog
        open={confirmDeleteId != null}
        onOpenChange={(open) => !open && setConfirmDeleteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete feedback?</AlertDialogTitle>
            <AlertDialogDescription>
              Bản ghi sẽ bị xoá vĩnh viễn khỏi database (không thể hoàn tác).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90"
              disabled={deleteFeedback.isPending}
              onClick={(e) => {
                e.preventDefault()
                if (!confirmDeleteId) return
                deleteFeedback.mutate(confirmDeleteId, {
                  onSuccess: () => {
                    toast.success("Đã xoá feedback.")
                    setConfirmDeleteId(null)
                    setDetailId(null)
                    clearSelection()
                  },
                  onError: (err) =>
                    toast.error(
                      err instanceof Error ? err.message : "Xoá thất bại."
                    ),
                })
              }}
            >
              Delete permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* confirm bulk delete */}
      <AlertDialog open={confirmBulk} onOpenChange={setConfirmBulk}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {selected.size} feedback đã chọn?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Tất cả bản ghi được chọn sẽ bị xoá vĩnh viễn khỏi database (không
              thể hoàn tác). Phân tích liên quan sẽ mất theo.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep them</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90"
              disabled={bulkDelete.isPending}
              onClick={(e) => {
                e.preventDefault()
                bulkDelete.mutate([...selected], {
                  onSuccess: ({ deleted }) => {
                    toast.success(`Đã xoá ${deleted} feedback.`)
                    setConfirmBulk(false)
                    clearSelection()
                  },
                  onError: (err) =>
                    toast.error(
                      err instanceof Error ? err.message : "Xoá thất bại."
                    ),
                })
              }}
            >
              Delete permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* confirm delete import batch */}
      <AlertDialog
        open={confirmImport != null}
        onOpenChange={(open) => !open && setConfirmImport(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete import{" "}
              {confirmImport?.original_filename ??
                confirmImport?.id.slice(0, 8) ??
                ""}{" "}
              ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ {confirmImport?.row_count ?? 0} feedback của lô import này
              cùng phân tích liên quan sẽ bị xoá vĩnh viễn (không thể hoàn tác).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90"
              disabled={deleteImport.isPending}
              onClick={(e) => {
                e.preventDefault()
                if (!confirmImport) return
                deleteImport.mutate(confirmImport.id, {
                  onSuccess: () => {
                    toast.success("Đã xoá import và toàn bộ dữ liệu liên quan.")
                    setConfirmImport(null)
                    if (activeImportId === confirmImport.id)
                      setActiveImportId(null)
                  },
                  onError: (err) =>
                    toast.error(
                      err instanceof Error ? err.message : "Xoá thất bại."
                    ),
                })
              }}
            >
              Delete permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <FeedbackDetailDrawer
        feedbackId={detailId}
        labelTopic={labelTopic}
        onClose={() => setDetailId(null)}
        onEdit={(item) => setEditing(item)}
        onDelete={(id) => setConfirmDeleteId(id)}
      />
    </div>
  )
}

export default function VaultPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <VaultWithParams />
    </Suspense>
  )
}

function VaultWithParams() {
  const params = useSearchParams()
  return <Vault initialImportId={params.get("import")} />
}

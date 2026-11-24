"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import type {
  ColumnFiltersState,
  ColumnVisibilityState,
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
  ArrowRight,
  Ban,
  ChevronDown,
  ChevronUp,
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  DataTableToolbar,
} from "@/components/data-table"
import { Textarea } from "@/components/ui/textarea"
import { apiFetch } from "@/lib/api"
import { useT } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { RUN_STATUS_TONE, SEVERITY_TONE } from "@/lib/tone"
import { ImportFileList } from "@/components/vault/import-file-list"
import { TopicPills } from "@/components/topic-pills"
import { NextStepBar } from "@/components/journey/next-step-bar"
import type {
  Feedback,
  FeedbackListResponse,
  ImportRecord,
  RunProgress,
  Severity,
} from "@/lib/types"
import { SEVERITY_LABEL } from "@/lib/labels"
import {
  useBulkDeleteFeedbacks,
  useDeleteFeedback,
  useDeleteImport,
  useFeedbackFacets,
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

// ── Cột metadata: khoá thật có trong file nhập (`data` / `source_meta`), mặc
// định ẩn, người dùng bật qua menu "Cột hiển thị" và lựa chọn được nhớ lại. ──
const METADATA_GROUP = {
  data: "Dữ liệu sản phẩm",
  source_meta: "Thông tin nguồn",
} as const
const metaColumnId = (zone: string, key: string) => `meta:${zone}:${key}`
function metaLabel(key: string): string {
  const spaced = key.replace(/[_-]+/g, " ").trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}
function parseColumnVisibility(raw: string): ColumnVisibilityState | null {
  const parsed: unknown = JSON.parse(raw)
  return parsed && typeof parsed === "object" && !Array.isArray(parsed)
    ? (parsed as ColumnVisibilityState)
    : null
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

const WIDE_VAULT_QUERY = "(min-width: 90rem)"

function subscribeToVaultWidth(onChange: () => void) {
  const media = window.matchMedia(WIDE_VAULT_QUERY)
  media.addEventListener("change", onChange)
  return () => media.removeEventListener("change", onChange)
}

function FeedbackDetailView({
  feedbackId,
  inline,
  labelTopic,
  position,
  onClose,
  onEdit,
  onDelete,
  onSelect,
  onPrev,
  onNext,
}: {
  feedbackId: string
  inline: boolean
  labelTopic: (topic: string) => string
  /** "3 / 20" trên trang hiện tại, null khi mục không nằm trong trang. */
  position: string | null
  onClose: () => void
  onEdit: (item: Feedback) => void
  onDelete: (id: string) => void
  onSelect: (id: string) => void
  onPrev: (() => void) | null
  onNext: (() => void) | null
}) {
  const detail = useFeedbackDetail(feedbackId)
  const similar = useSimilarFeedbacks(feedbackId)
  const item = detail.data
  const analysis = item?.ai_analysis ?? null
  const severity = analysis?.severity

  // Phím ↑/↓ (hoặc k/j) đi qua từng phản hồi khi panel đang mở, trừ khi đang gõ.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target?.closest("input, textarea, select, [contenteditable=true], [role=dialog]")) return
      if ((event.key === "ArrowDown" || event.key === "j") && onNext) {
        event.preventDefault()
        onNext()
      } else if ((event.key === "ArrowUp" || event.key === "k") && onPrev) {
        event.preventDefault()
        onPrev()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onNext, onPrev])

  const detailLabel = `F-${item?.id.slice(0, 8) ?? feedbackId.slice(0, 8)}`
  const exploreHref = item
    ? `/data-graph?import=${item.import_id ?? ""}${
        analysis?.topics?.[0] ? `&topic=${encodeURIComponent(analysis.topics[0])}` : ""
      }`
    : "/data-graph"

  const navigator = (
    <div className="flex items-center gap-1">
      {position ? (
        <span className="mr-1 font-mono text-xs whitespace-nowrap text-muted-foreground">{position}</span>
      ) : null}
      <Button type="button" variant="ghost" size="icon-sm" aria-label="Phản hồi trước (phím ↑)" disabled={!onPrev} onClick={() => onPrev?.()}>
        <ChevronUp />
      </Button>
      <Button type="button" variant="ghost" size="icon-sm" aria-label="Phản hồi sau (phím ↓)" disabled={!onNext} onClick={() => onNext?.()}>
        <ChevronDown />
      </Button>
    </div>
  )

  const content = item ? (
    <div className="flex min-w-0 flex-col gap-5 px-4 pb-4">
      <blockquote className="border-l-2 border-signal/60 pl-3 text-sm leading-relaxed whitespace-pre-wrap wrap-anywhere">
        {item.feedback_text ?? "—"}
      </blockquote>

      <div className="flex flex-wrap items-center gap-2">
        <SentimentIndicator value={analysis?.sentiment} />
        {severity ? (
          <Badge variant={SEVERITY_TONE[severity] ?? "secondary"}>
            {SEVERITY_LABEL.vi[severity as Severity] ?? severity}
          </Badge>
        ) : null}
        <Badge variant={analysis ? "success" : "warning"}>
          {analysis ? "Đã phân loại" : "Chờ phân loại"}
        </Badge>
      </div>

      <section className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Nhãn</h3>
        <div className="flex min-w-0 flex-wrap gap-1">
          {analysis?.uncategorized ? <Badge variant="outline">Chưa có chủ đề phù hợp</Badge> : null}
          {(analysis?.topics ?? []).map((t) => (
            <Badge key={t} variant="secondary" title={t}>
              {labelTopic(t)}
            </Badge>
          ))}
          {(analysis?.emotions ?? []).map((e) => (
            <Badge key={e} variant="outline">
              {e}
            </Badge>
          ))}
          {!analysis ? <span className="text-sm text-muted-foreground">Phân loại để AI gắn chủ đề và cảm xúc.</span> : null}
        </div>
      </section>

      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Nguồn</dt>
        <dd className="truncate">{item.source || "—"}</dd>
        <dt className="text-muted-foreground">Ngày</dt>
        <dd className="font-mono text-xs leading-5">{shortDate(item.occurred_at)}</dd>
        {analysis?.intent ? (
          <>
            <dt className="text-muted-foreground">Ý định</dt>
            <dd>{analysis.intent}</dd>
          </>
        ) : null}
        <dt className="text-muted-foreground">Lô nhập</dt>
        <dd className="truncate font-mono text-xs leading-5" title={item.import_id ?? undefined}>
          {item.import_id ? item.import_id.slice(0, 8) : "—"}
        </dd>
      </dl>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" asChild>
          <Link href={exploreHref}>
            Điều tra chủ đề này
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
        <Button size="sm" variant="ghost" asChild>
          <Link href={`/feedbacks/${item.id}`}>Mở trang đầy đủ</Link>
        </Button>
      </div>

      <section className="flex flex-col gap-2 border-t pt-4">
        <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Phản hồi tương tự</h3>
        {similar.isPending ? (
          <Spinner />
        ) : similar.data && similar.data.length ? (
          <ul className="flex flex-col gap-1.5">
            {/* Dữ liệu nhập lặp lại cùng một câu ở nhiều file — chỉ hiện mỗi
                nội dung một lần, giữ bản giống nhất. */}
            {similar.data
              .filter((s, i, all) => all.findIndex((o) => (o.snippet ?? o.id) === (s.snippet ?? s.id)) === i)
              .map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => onSelect(s.id)}
                  className="flex w-full flex-col gap-1 rounded-lg border bg-card p-2.5 text-left text-sm transition-colors hover:bg-accent/60 focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="line-clamp-2">{s.snippet ?? "—"}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    Giống {Math.round(s.score * 100)}%
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Cần phân loại phản hồi này trước thì mới tìm được phản hồi tương tự.
          </p>
        )}
      </section>
    </div>
  ) : detail.isError ? (
    <div className="px-4 pb-4">
      <Alert variant="destructive">
        <AlertTitle>Chưa tải được phản hồi</AlertTitle>
        <AlertDescription>
          <Button variant="outline" size="sm" onClick={() => void detail.refetch()}>
            Thử lại
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  ) : (
    <div className="flex flex-col gap-3 px-4 pb-4">
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-16 w-full" />
    </div>
  )

  const editActions = item ? (
    <>
      <Button type="button" variant="ghost" size="icon-sm" aria-label="Sửa phản hồi" onClick={() => onEdit(item)}>
        <Pencil />
      </Button>
      <Button type="button" variant="ghost" size="icon-sm" aria-label="Xoá phản hồi" onClick={() => onDelete(item.id)}>
        <Trash2 />
      </Button>
    </>
  ) : null

  if (inline) {
    return (
      <aside
        aria-label="Chi tiết phản hồi"
        className="sticky top-20 flex max-h-[calc(100dvh-6rem)] min-w-0 flex-col self-start overflow-hidden rounded-xl border bg-card"
      >
        {/* Hai hàng: tên + đóng ở trên, điều hướng + sửa/xoá ở dưới — một hàng
            ở panel 22rem làm tiêu đề và "1 / 20" bị gãy dòng. */}
        <header className="flex flex-col gap-1 border-b px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex min-w-0 items-baseline gap-2 text-sm font-medium">
              <span className="truncate">Chi tiết phản hồi</span>
              <span className="shrink-0 font-mono text-xs font-normal text-signal">{detailLabel}</span>
            </h2>
            <Button type="button" variant="ghost" size="icon-sm" aria-label="Đóng chi tiết phản hồi" onClick={onClose}>
              <X />
            </Button>
          </div>
          <div className="-ml-1 flex items-center justify-between">
            {navigator}
            <div className="flex items-center">{editActions}</div>
          </div>
        </header>
        <div className="min-h-0 overflow-y-auto pt-4">{content}</div>
      </aside>
    )
  }

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="font-mono text-signal">{detailLabel}</SheetTitle>
          <SheetDescription>Chi tiết phản hồi</SheetDescription>
          <div className="flex items-center gap-1 pt-1">
            {navigator}
            {editActions}
          </div>
        </SheetHeader>
        {content}
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
  const t = useT().vault
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
        toast.success(t.toastDone)
      } else if (data.status === "failed") {
        toast.error(t.toastFailed)
      }
    }
    prevStatus.current = data.status
  }, [data, qc, t])

  if (!data) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {data.status === "running" ? <Spinner /> : null}
          {t.runTitle}
        </CardTitle>
        <CardDescription>{t.runLeave}</CardDescription>
        <CardAction>
          <Badge variant={RUN_STATUS_TONE[data.status] ?? "secondary"}>
            {t.runStatus[data.status] ?? data.status}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="gap-2">
        <Progress value={pct} />
        <p className="font-mono text-sm">
          {data.processed_count} / {data.total_count}
        </p>
        {data.status === "completed" ? (
          <div className="mt-2 flex flex-col gap-1 rounded-lg bg-secondary/40 p-3">
            <p className="text-sm font-medium">{t.nextTitle}</p>
            <p className="text-xs text-muted-foreground">{t.nextBody}</p>
          </div>
        ) : null}
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
                  toast.success(t.stopRequested)
                  void qc.invalidateQueries({ queryKey: ["feedbacks"] })
                },
              })
            }
          >
            <Ban data-icon="inline-start" />
            {data.cancel_requested_at ? t.stopping : t.stop}
          </Button>
        ) : (
          <div className="flex w-full flex-wrap items-center justify-between gap-2">
            <Button size="sm" variant="ghost" onClick={onDismiss}>
              {t.closeCard}
            </Button>
            {data.status === "completed" ? (
              <Button asChild>
                <Link href="/data-graph?ask=1">
                  {t.nextCta}
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            ) : null}
          </div>
        )}
      </CardFooter>
    </Card>
  )
}

function Vault({
  initialImportId,
  initialItemId,
  analyzeIntent,
  reclassifyIntent,
}: {
  initialImportId: string | null
  /** ?item= — phản hồi đang mở trong panel chi tiết; giữ qua refresh/back. */
  initialItemId: string | null
  /** ?analyze=1 từ lộ trình / kết quả import: mở biên nhận phân loại ngay. */
  analyzeIntent: boolean
  /** ?reclassify=1: mở khoá mục UNCATEGORIZED rồi mở biên nhận. */
  reclassifyIntent: boolean
}) {
  const t = useT()
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
  // Bộ lọc chủ đề là bộ lọc cột (đa chọn, khớp bất kỳ — feedback mang tới 3 chủ đề).
  const topicFilter = useMemo(
    () => (columnFilters.find((f) => f.id === "topics")?.value as string[] | undefined) ?? [],
    [columnFilters],
  )
  const [analysisState, setAnalysisState] = useState<string>("")
  const detailId = initialItemId
  const setDetailId = (id: string | null) => {
    const qs = new URLSearchParams()
    if (activeImportId) qs.set("import", activeImportId)
    if (id) qs.set("item", id)
    const query = qs.toString()
    router.replace(query ? `/vault?${query}` : "/vault", { scroll: false })
  }
  const supportsInlineDetails = useSyncExternalStore(
    subscribeToVaultWidth,
    () => window.matchMedia(WIDE_VAULT_QUERY).matches,
    () => false
  )
  const showInlineDetails = supportsInlineDetails && detailId != null
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

  // Chủ đề và khoá metadata có THẬT trong phạm vi đang xem (product + lô nhập).
  // Trước đây bộ lọc chủ đề lấy cả taxonomy của product, nên liệt kê cả chủ đề
  // không hề có trong lô này. Lỗi (vd. backend chưa cập nhật) → rơi về taxonomy.
  const facets = useFeedbackFacets({ productId, importId: activeImportId })
  const facetTopics = facets.data?.topics
  const metadataFacets = facets.data?.metadata
  const topicFilterOptions = useMemo(() => {
    const options: { value: string; label: string; count?: number }[] =
      facetTopics
        ? facetTopics.map((f) => ({
            value: f.value,
            label: labelTopic(f.value),
            count: f.count,
          }))
        : topicOptions.map((n) => ({
            value: n.slug ?? n.name,
            label: n.name_vi ?? n.name,
          }))
    // Chủ đề đang chọn mà phạm vi mới không còn: vẫn hiện để bỏ chọn được.
    for (const slug of topicFilter)
      if (!options.some((o) => o.value === slug))
        options.unshift({ value: slug, label: labelTopic(slug), count: 0 })
    return options
  }, [facetTopics, topicOptions, labelTopic, topicFilter])

  // Cột hiển thị được nhớ trên máy; cột metadata chưa từng chọn thì mặc định ẩn.
  const [storedVisibility, setStoredVisibility] =
    useStoredState<ColumnVisibilityState>(
      "vault.columns.v1",
      {},
      parseColumnVisibility,
    )
  const columnVisibility = useMemo(() => {
    // "Nguồn" mặc định ẩn: nó hiện ở dòng phụ của cột "Phản hồi", nhường chỗ
    // cho bảng vừa khít khung. Bật lại ở menu "Chọn cột hiển thị".
    const base: ColumnVisibilityState = { source: false }
    for (const m of metadataFacets ?? []) base[metaColumnId(m.zone, m.key)] = false
    // "sentiment" chỉ là cột để bộ lọc Cảm xúc bám vào, không hiển thị.
    return { ...base, ...storedVisibility, sentiment: false }
  }, [metadataFacets, storedVisibility])

  const filters = {
    page,
    pageSize,
    // Luôn giới hạn trong product đang mở: không có product_id, "Tất cả file"
    // trước đây trả cả feedback của product khác (tổng số và chủ đề bị lẫn).
    productId: productId ?? undefined,
    importId: activeImportId ?? undefined,
    analysisState: (analysisState || undefined) as
      | "pending"
      | "completed"
      | "uncategorized"
      | undefined,
    sentiment:
      (columnFilters.find((f) => f.id === "sentiment")?.value as string[]) ??
      undefined,
    topic: topicFilter.length ? topicFilter : undefined,
    q: debouncedQ.trim() || undefined,
    sort: sortingToServerSort(sorting),
  }
  const feedbacks = useFeedbacks(filters)
  const rows = useMemo(() => feedbacks.data?.items ?? [], [feedbacks.data])

  const pendingCount = useQuery({
    queryKey: ["feedbacks", "pending-count", productId, activeImportId],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=pending${
          productId ? `&product_id=${productId}` : ""
        }${activeImportId ? `&import_id=${activeImportId}` : ""}`
      ),
    staleTime: 15_000,
  })

  // Mục THẬT SỰ chạy được = chờ phân loại và chưa bị lượt nào giữ. `pending`
  // ở trên còn tính cả mục đang nằm trong lượt đang chạy; dùng nó để chọn file
  // chạy tiếp ở "All imports" từng chọn nhầm file đang chạy → biên nhận 0 mục
  // → server từ chối 422 (QA HN-013, 2026-11-11).
  const eligibleCount = useQuery({
    queryKey: ["feedbacks", "eligible-count", productId, activeImportId],
    queryFn: () =>
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=1&analysis_state=eligible${
          productId ? `&product_id=${productId}` : ""
        }${activeImportId ? `&import_id=${activeImportId}` : ""}`
      ),
    staleTime: 5_000,
  })
  const pendingTotal = pendingCount.data?.total ?? 0
  const eligibleTotal = eligibleCount.data?.total ?? pendingTotal
  // Còn mục chờ nhưng tất cả đang nằm trong lượt đang chạy.
  const allPendingBusy = pendingTotal > 0 && eligibleTotal === 0

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
  // "All imports" (không chọn file): lượt đang chạy của BẤT KỲ file nào thuộc
  // sản phẩm này đều phải hiện tiến độ và khoá nút, không chỉ file đang chọn.
  const activeRunId =
    startedRunId ??
    runningRun.data?.items.find(
      (r) =>
        r.import_id &&
        (activeImportId
          ? r.import_id === activeImportId
          : imports.some((i) => i.id === r.import_id))
    )?.id ??
    null

  // Đang có run chạy cho file này → khoá nút phân loại, tránh bấm chồng lượt.
  const activeRun = useRunProgress(activeRunId)
  const classifying = activeRun.data?.status === "running"

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
          trigger.reset()
          void qc.invalidateQueries({ queryKey: ["feedbacks"] })
        },
        // Lỗi hiện NGAY TRONG hộp biên nhận (trigger.error) kèm nút xem lại
        // ước tính — toast tự biến mất khiến người dùng không biết vì sao hộp
        // thoại đứng yên (QA HN-013).
        onError: () => void qc.invalidateQueries({ queryKey: ["feedbacks"] }),
      }
    )
  }

  const refreshReceipt = () => {
    if (!receiptScope) return
    trigger.reset()
    void preview.mutateAsync(receiptScope).catch(() => undefined)
  }

  const receiptScopeFor = (): Scope | null => {
    const scope: Scope =
      selectedPending.length > 0 && activeImportId
        ? {
            mode: "selected",
            import_id: activeImportId,
            feedback_ids: selectedPending,
          }
        : activeImportId
          ? { mode: "batch", import_id: activeImportId }
          : {
              // "All imports": phân loại theo file còn mục THẬT SỰ chạy được
              // (chưa bị lượt nào giữ) — không phải file đầu danh sách, cũng
              // không phải file đang chạy dở.
              mode: "batch",
              import_id:
                eligibleCount.data?.items[0]?.import_id ??
                pendingCount.data?.items[0]?.import_id ??
                imports[0]?.id ??
                "",
            }
    return scope.import_id ? scope : null
  }

  // Ước tính trước, chỉ mở biên nhận khi server đã trả preview.
  const requestReceipt = (scope: Scope) =>
    preview.mutateAsync(scope).then(
      () => setReceiptScope(scope),
      (err) =>
        toast.error(
          err instanceof Error ? err.message : "Chưa ước tính được lượt phân loại."
        )
    )

  const openReceipt = () => {
    if (!productId) return
    const scope = receiptScopeFor()
    if (!scope) {
      toast.error(t.vault.chooseImport)
      return
    }
    void requestReceipt(scope)
  }

  // Mở khoá các mục UNCATEGORIZED rồi mở luôn biên nhận phân loại cho file có
  // mục vừa mở khoá — người dùng chỉ còn một bước xác nhận chi phí.
  const unlockAndClassify = () => {
    if (!productId) return
    reEnrich
      .mutateAsync({ product_id: productId })
      .then(async (res) => {
        void qc.invalidateQueries({ queryKey: ["feedbacks"] })
        if (res.released === 0) {
          toast.info("Không có phản hồi nào cần mở khoá.")
          return
        }
        toast.success(`Đã mở khoá ${res.released} phản hồi để phân loại lại.`)
        const next = await apiFetch<FeedbackListResponse>(
          `/api/feedbacks?limit=1&analysis_state=eligible&product_id=${productId}`
        )
        const importId = activeImportId ?? next.items[0]?.import_id
        if (importId) void requestReceipt({ mode: "batch", import_id: importId })
      })
      .catch((err) =>
        toast.error(
          err instanceof Error ? err.message : "Không mở khoá được phản hồi."
        )
      )
  }

  // Intent ?reclassify=1 từ lộ trình: chạy đúng một lần.
  const reclassifyHandled = useRef(false)
  useEffect(() => {
    if (!reclassifyIntent || reclassifyHandled.current || !productId) return
    reclassifyHandled.current = true
    router.replace(activeImportId ? `/vault?import=${activeImportId}` : "/vault", {
      scroll: false,
    })
    unlockAndClassify()
  })

  // Intent ?analyze=1: mở biên nhận đúng một lần khi số mục chờ đã có, rồi gỡ
  // param để refresh/back không mở lại.
  const analyzeHandled = useRef(false)
  useEffect(() => {
    if (!analyzeIntent || analyzeHandled.current) return
    if (
      !productId ||
      !pendingCount.isSuccess ||
      !eligibleCount.isSuccess ||
      preview.isPending
    )
      return
    analyzeHandled.current = true
    router.replace(activeImportId ? `/vault?import=${activeImportId}` : "/vault", {
      scroll: false,
    })
    const scope = receiptScopeFor()
    if (scope && eligibleTotal > 0) void requestReceipt(scope)
  })

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
    columnFilters.length > 0 || debouncedQ.trim() !== "" || analysisState !== ""
  function clearAllFilters() {
    setQInput("")
    setColumnFilters([])
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
        // Cố định ở mép trái cùng cột "Phản hồi" khi cuộn ngang.
        meta: {
          thClassName: "w-10 min-w-10 max-w-10",
          tdClassName: "w-10 min-w-10 max-w-10",
          stickyLeft: "0px",
        },
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
        meta: {
          label: "Phản hồi",
          thClassName: "w-[40%] min-w-56",
          tdClassName: "min-w-56 whitespace-normal",
          stickyLeft: "2.5rem", // = độ rộng cột chọn dòng (w-10)
          stickyEdge: true,
        },
        header: "Phản hồi",
        cell: ({ row, table }) => (
          <>
            <button
              type="button"
              className="line-clamp-2 max-w-xl rounded-sm text-left text-sm hover:underline focus-visible:outline-2 focus-visible:outline-ring"
              onClick={(event) => {
                event.stopPropagation()
                setDetailId(row.original.id)
              }}
            >
              {row.original.feedback_text ?? "—"}
            </button>
            {row.original.pii_detected ? (
              <Badge variant="outline" className="ml-2">
                Đã ẩn PII
              </Badge>
            ) : null}
            {/* Cột "Nguồn" đang ẩn → nguồn hiện ngay dưới nội dung. */}
            {table.getColumn("source")?.getIsVisible() ? null : (
              <span className="mt-0.5 block text-[11px] text-muted-foreground">
                {row.original.source}
              </span>
            )}
          </>
        ),
      },
      {
        id: "source",
        accessorFn: (f: Feedback) => f.source,
        meta: { label: "Nguồn" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Nguồn" />
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
        meta: { label: "Ngày" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Ngày" />
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
        meta: { label: "Mức độ" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Mức độ" />
        ),
        cell: ({ row }) => {
          const severity = row.original.ai_analysis?.severity
          if (!severity) return <span className="text-muted-foreground">—</span>
          return (
            <Badge variant={SEVERITY_TONE[severity] ?? "secondary"}>
              {SEVERITY_LABEL.vi[severity as Severity] ?? severity}
            </Badge>
          )
        },
      },
      {
        id: "sentiment",
        // Cột ẩn chỉ để bộ lọc "Sentiment" ở toolbar có chỗ bám; lọc chạy ở server.
        accessorFn: (f: Feedback) => f.ai_analysis?.sentiment ?? "",
        enableSorting: false,
        enableHiding: false,
        meta: { label: "Cảm xúc" },
        cell: () => null,
      },
      {
        id: "topics",
        // accessorFn để cột lọc được (bộ lọc "Chủ đề" ở toolbar); lọc chạy ở server.
        accessorFn: (f: Feedback) => f.ai_analysis?.topics ?? [],
        enableSorting: false,
        meta: { label: "Chủ đề", tdClassName: "min-w-40 max-w-72 whitespace-normal" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Chủ đề" />
        ),
        // Mỗi phản hồi mang tới 3 chủ đề → hiện đủ dạng tag pill.
        cell: ({ row }) => (
          <TopicPills
            topics={row.original.ai_analysis?.topics}
            uncategorized={Boolean(row.original.ai_analysis?.uncategorized)}
            label={labelTopic}
          />
        ),
      },
      {
        id: "state",
        enableSorting: false,
        enableHiding: false,
        meta: { label: "Trạng thái" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Trạng thái" />
        ),
        cell: ({ row }) => {
          const ready = Boolean(row.original.ai_analysis)
          return (
            <Badge variant={ready ? "success" : "warning"}>
              {ready ? "Đã phân loại" : "Chờ phân loại"}
            </Badge>
          )
        },
      },
      ...(metadataFacets ?? []).map(
        (m): LegacyColumnDef<Feedback> => ({
          id: metaColumnId(m.zone, m.key),
          accessorFn: (f: Feedback) => f[m.zone]?.[m.key] ?? "",
          enableSorting: false,
          meta: { label: metaLabel(m.key), group: METADATA_GROUP[m.zone] },
          header: ({ column }) => (
            <DataTableColumnHeader column={column} title={metaLabel(m.key)} />
          ),
          cell: ({ row }) => {
            const value = row.original[m.zone]?.[m.key]
            return value ? (
              <span
                title={String(value)}
                className="block max-w-48 truncate text-sm text-muted-foreground"
              >
                {String(value)}
              </span>
            ) : (
              <span className="text-muted-foreground">—</span>
            )
          },
        }),
      ),
    ],
    [labelTopic, metadataFacets],
  )

  const table = useLegacyTable({
    data: rows,
    columns,
    getRowId: (f) => f.id,
    manualPagination: true,
    pageCount,
    rowCount: total,
    manualSorting: true,
    manualFiltering: true,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    state: { sorting, columnFilters, rowSelection, pagination, columnVisibility },
    onColumnVisibilityChange: (updater) =>
      setStoredVisibility(
        typeof updater === "function" ? updater(columnVisibility) : updater,
      ),
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

  const detailIndex = detailId ? rows.findIndex((r) => r.id === detailId) : -1
  const prevRow = detailIndex > 0 ? rows[detailIndex - 1] : null
  const nextRow = detailIndex >= 0 && detailIndex < rows.length - 1 ? rows[detailIndex + 1] : null
  const feedbackDetail = detailId ? (
    <FeedbackDetailView
      feedbackId={detailId}
      inline={showInlineDetails}
      labelTopic={labelTopic}
      position={detailIndex >= 0 ? `${detailIndex + 1} / ${rows.length}` : null}
      onClose={() => setDetailId(null)}
      onEdit={setEditing}
      onDelete={setConfirmDeleteId}
      onSelect={setDetailId}
      onPrev={prevRow ? () => setDetailId(prevRow.id) : null}
      onNext={nextRow ? () => setDetailId(nextRow.id) : null}
    />
  ) : null

  return (
    <div className="flex flex-col gap-6">
      <NextStepBar />
      <PageHeader
        title={t.nav.items.vault}
        description="Duyệt từng phản hồi, gắn nhãn hàng loạt, và chạy phân loại có kiểm soát."
        actions={
          <Button asChild variant="outline">
            <Link href="/importer?new=1">{t.importer.result.another}</Link>
          </Button>
        }
      />

      <div className={cn(
        "grid min-w-0 gap-6 lg:grid-cols-[248px_minmax(0,1fr)]",
        showInlineDetails && "lg:grid-cols-[12rem_minmax(0,1fr)_22rem]"
      )}>
        <ImportFileList
          imports={imports}
          activeId={activeImportId}
          loading={importsQuery.isPending}
          onSelectAll={() => {
            setActiveImportId(null)
            clearSelection()
            setColumnFilters((old) => old.filter((f) => f.id !== "topics"))
            setPage(1)
          }}
          onSelect={(item) => {
            setActiveImportId(item.id)
            clearSelection()
            setColumnFilters((old) => old.filter((f) => f.id !== "topics"))
            setPage(1)
          }}
          onDelete={setConfirmImport}
        />

        <div className="flex min-w-0 flex-col gap-4">
          <DataTableToolbar
            table={table}
            onResetColumns={() => setStoredVisibility({})}
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
                title: "Cảm xúc",
                options: [
                  { value: "negative", label: "Tiêu cực", count: null },
                  { value: "neutral", label: "Trung lập", count: null },
                  { value: "positive", label: "Tích cực", count: null },
                  { value: "mixed", label: "Hỗn hợp", count: null },
                ],
              },
              {
                // Đa chọn, khớp bất kỳ; số lượng theo phạm vi đang xem (facets).
                columnId: "topics",
                title: "Chủ đề",
                options: topicFilterOptions,
              },
            ]}
          >
            <Select
              value={analysisState}
              onValueChange={(v) => {
                setAnalysisState(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger size="sm" className="w-48">
                <SelectValue placeholder="Trạng thái phân loại" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Mọi trạng thái</SelectItem>
                <SelectItem value="pending">Chờ phân loại</SelectItem>
                <SelectItem value="completed">Đã phân loại</SelectItem>
                <SelectItem value="uncategorized">Chưa có chủ đề</SelectItem>
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
          {/* Chưa có chủ đề nào thì phân loại lại vẫn ra UNCATEGORIZED — lộ
              trình phía trên đã dẫn sang bước tạo bộ chủ đề. */}
          {(pendingCount.data?.total ?? 0) === 0 &&
          (uncategorizedCount.data?.total ?? 0) > 0 &&
          (taxonomy.data?.items ?? []).some((n) => n.status === "active") ? (
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
                onClick={unlockAndClassify}
              >
                {reEnrich.isPending ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <Unlock data-icon="inline-start" />
                )}
                {t.journey.next.reclassify.cta}
              </Button>
            </div>
          ) : null}

          <Card className="gap-0 py-0">
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
                ) : allPendingBusy ? (
                  <>{t.vault.busyLine(pendingTotal)}</>
                ) : (
                  <>{t.vault.pendingLine(pendingTotal)}</>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  onClick={openReceipt}
                  disabled={
                    preview.isPending ||
                    classifying ||
                    (selectedPending.length === 0 && eligibleTotal === 0)
                  }
                >
                  {preview.isPending ? (
                    <Spinner data-icon="inline-start" />
                  ) : (
                    <Play data-icon="inline-start" />
                  )}
                  {t.vault.analyze(selectedPending.length || eligibleTotal)}
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
                  Khám phá mục đã chọn
                </Button>
              </div>
            </div>
            <CardContent className="p-0">
              <DataTable
                table={table}
                isLoading={feedbacks.isFetching && !feedbacks.data}
                maxHeightClass="max-h-[65vh]"
                onRowClick={(row) => setDetailId(row.id)}
                isRowActive={(row) => row.id === detailId}
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
            <CardFooter className="flex-col items-stretch border-t pb-(--card-spacing)">
              <DataTablePagination table={table} />
            </CardFooter>
          </Card>
        </div>
        {showInlineDetails ? feedbackDetail : null}
      </div>

      {/* L05 — analysis receipt */}
      <AlertDialog
        open={receiptScope != null}
        onOpenChange={(open) => {
          if (!open) {
            setReceiptScope(null)
            preview.reset()
            trigger.reset()
          }
        }}
      >
        <AlertDialogContent className="sm:max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>{t.vault.receiptTitle}</AlertDialogTitle>
            <AlertDialogDescription>
              {product?.name ?? "—"} · {t.vault.receiptFile}:{" "}
              {imports.find((i) => i.id === receiptScope?.import_id)
                ?.original_filename ?? receiptScope?.import_id.slice(0, 8)}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {preview.data && preview.data.selected_count === 0 ? (
            <Alert>
              <AlertTitle>{t.vault.receiptNothingTitle}</AlertTitle>
              <AlertDescription>{t.vault.receiptNothingBody}</AlertDescription>
            </Alert>
          ) : preview.data ? (
            <p className="font-heading text-lg">
              {t.vault.receiptHeadline(preview.data.selected_count)}
            </p>
          ) : null}
          {/* "All imports": nói rõ lượt này chỉ chạy MỘT file và còn bao nhiêu
              mục ở file khác — tránh hiểu nhầm đã phân loại toàn bộ (HN-005). */}
          {preview.data &&
          preview.data.selected_count > 0 &&
          !activeImportId &&
          eligibleTotal > preview.data.eligible_count ? (
            <p className="text-sm text-muted-foreground">
              {t.vault.receiptOtherFiles(
                eligibleTotal - preview.data.eligible_count
              )}
            </p>
          ) : null}
          {trigger.isError ? (
            <Alert variant="destructive" role="alert">
              <AlertTitle>{t.vault.receiptStartFailed}</AlertTitle>
              <AlertDescription className="flex flex-col gap-3">
                <span>{trigger.error.message}</span>
                <div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={preview.isPending}
                    onClick={refreshReceipt}
                  >
                    {preview.isPending ? (
                      <Spinner data-icon="inline-start" />
                    ) : null}
                    {t.vault.receiptRefresh}
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          ) : null}
          {preview.data ? (
            <div className="grid grid-cols-2 gap-2 rounded-lg bg-secondary/50 p-3 text-sm sm:grid-cols-3">
              <span>
                <strong className="font-mono">
                  {preview.data.selected_count}
                </strong>
                <br />
                {t.vault.inScope}
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.logical_classify_requests}
                </strong>
                <br />
                {t.vault.classifyCalls}
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.logical_embedding_requests}
                </strong>
                <br />
                {t.vault.embedCalls}
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.max_provider_attempts}
                </strong>
                <br />
                {t.vault.maxAttempts}
              </span>
              <span>
                <strong className="font-mono">
                  ~{preview.data.estimated_input_tokens}
                </strong>
                <br />
                {t.vault.inputTokens}
              </span>
              <span>
                <strong className="font-mono">
                  {preview.data.remaining_count}
                </strong>
                <br />
                {t.vault.remaining}
              </span>
            </div>
          ) : (
            <Spinner />
          )}
          <p className="text-xs text-muted-foreground">{t.vault.receiptNote}</p>
          <AlertDialogFooter>
            <AlertDialogCancel>{t.vault.back}</AlertDialogCancel>
            <AlertDialogAction
              disabled={
                !preview.data ||
                preview.isPending ||
                preview.data.selected_count === 0 ||
                trigger.isPending
              }
              onClick={(e) => {
                e.preventDefault()
                startAnalysis()
              }}
            >
              {trigger.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Play data-icon="inline-start" />
              )}
              {t.vault.start}
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
            <AlertDialogTitle>Xoá phản hồi này?</AlertDialogTitle>
            <AlertDialogDescription>
              Bản ghi sẽ bị xoá vĩnh viễn khỏi database (không thể hoàn tác).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
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
              Xoá vĩnh viễn
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* confirm bulk delete */}
      <AlertDialog open={confirmBulk} onOpenChange={setConfirmBulk}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Xoá {selected.size} phản hồi đã chọn?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Tất cả bản ghi được chọn sẽ bị xoá vĩnh viễn khỏi database (không
              thể hoàn tác). Phân tích liên quan sẽ mất theo.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
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
              Xoá vĩnh viễn
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
              Xoá lô nhập{" "}
              {confirmImport?.original_filename ??
                confirmImport?.id.slice(0, 8) ??
                ""}
              ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ {confirmImport?.row_count ?? 0} feedback của lô import này
              cùng phân tích liên quan sẽ bị xoá vĩnh viễn (không thể hoàn tác).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
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
              Xoá vĩnh viễn
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {showInlineDetails ? null : feedbackDetail}
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
  return (
    <Vault
      initialImportId={params.get("import")}
      initialItemId={params.get("item")}
      analyzeIntent={params.get("analyze") === "1"}
      reclassifyIntent={params.get("reclassify") === "1"}
    />
  )
}

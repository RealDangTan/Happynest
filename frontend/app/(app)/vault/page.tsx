"use client"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Ban,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  Pencil,
  Play,
  Search,
  Trash2,
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
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { apiFetch } from "@/lib/api"
import type {
  Feedback,
  FeedbackListResponse,
  ImportRecord,
  RunProgress,
} from "@/lib/types"
import {
  FEEDBACKS_PAGE_SIZE,
  useBulkDeleteFeedbacks,
  useDeleteFeedback,
  useDeleteImport,
  useFeedbacks,
  useUpdateFeedback,
} from "@/hooks/use-feedbacks"
import {
  useAnalysisPreview,
  useCancelRun,
  useRunProgress,
  useTriggerRun,
} from "@/hooks/use-analysis"
import {
  useFeedbackDetail,
  useSimilarFeedbacks,
} from "@/hooks/use-feedback-detail"
import { PageHeader } from "@/components/page-header"
import { useProduct } from "@/hooks/use-product"
import { shortDate } from "@/lib/graph"

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
  onClose,
  onEdit,
  onDelete,
}: {
  feedbackId: string | null
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
                            className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                          >
                            {t}
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
                  <span>{analysis?.sentiment ?? "—"}</span>
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

function RunningAnalysisCard({ runId }: { runId: string }) {
  const run = useRunProgress(runId)
  const cancel = useCancelRun()
  const qc = useQueryClient()
  const data: RunProgress | undefined = run.data
  const pct = data?.total_count
    ? Math.round((data.processed_count / data.total_count) * 100)
    : 0

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
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              void qc.invalidateQueries({ queryKey: ["feedbacks"] })
            }
          >
            Refresh results
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
  const [page, setPage] = useState(1)
  const [topic, setTopic] = useState<string>("")
  const [sentiment, setSentiment] = useState<string>("")
  const [analysisState, setAnalysisState] = useState<string>("")
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailId, setDetailId] = useState<string | null>(null)
  const [receiptScope, setReceiptScope] = useState<Scope | null>(null)
  const [startedRunId, setStartedRunId] = useState<string | null>(null)

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

  const filters = {
    page,
    importId: activeImportId ?? undefined,
    analysisState: (analysisState || undefined) as
      "pending" | "completed" | undefined,
    sentiment: sentiment || undefined,
    topic: topic || undefined,
  }
  const feedbacks = useFeedbacks(filters)
  const rows = useMemo(() => feedbacks.data?.items ?? [], [feedbacks.data])
  const filteredRows = useMemo(() => {
    if (!search.trim()) return rows
    const q = search.toLowerCase()
    return rows.filter((r) => (r.feedback_text ?? "").toLowerCase().includes(q))
  }, [rows, search])

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

  const preview = useAnalysisPreview()
  const trigger = useTriggerRun()

  // A running scoped analysis for this import (e.g. reopened from Current tasks).
  const runningRun = useQuery({
    queryKey: ["analysis", "runs", "vault-active", activeImportId],
    queryFn: () =>
      apiFetch<{ items: RunProgress[] }>(
        `/api/analysis/runs?limit=10&status=running`
      ),
    refetchInterval: 6000,
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

  const total = filteredRows.length
  const totalPages = Math.max(
    1,
    Math.ceil((feedbacks.data?.total ?? 0) / FEEDBACKS_PAGE_SIZE)
  )

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
              setSelected(new Set())
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
                setSelected(new Set())
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
          <div className="flex flex-wrap items-center gap-2">
            <InputGroup className="min-w-52 flex-1 sm:max-w-xs">
              <InputGroupAddon>
                <Search />
              </InputGroupAddon>
              <InputGroupInput
                placeholder="Search feedback…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </InputGroup>
            <Select
              value={topic}
              onValueChange={(v) => {
                setTopic(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Topic" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Topic: any</SelectItem>
                <SelectItem value="Performance">Performance</SelectItem>
                <SelectItem value="Accuracy">Accuracy</SelectItem>
                <SelectItem value="Reliability">Reliability</SelectItem>
                <SelectItem value="Speed">Speed</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={sentiment}
              onValueChange={(v) => {
                setSentiment(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Sentiment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Sentiment: any</SelectItem>
                <SelectItem value="negative">Negative</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
                <SelectItem value="positive">Positive</SelectItem>
                <SelectItem value="mixed">Mixed</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={analysisState}
              onValueChange={(v) => {
                setAnalysisState(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Analysis state" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Analysis: any</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="completed">Ready</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {activeRunId ? <RunningAnalysisCard runId={activeRunId} /> : null}

          <Card className="py-0">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <span className="sr-only">Select</span>
                    </TableHead>
                    <TableHead>Feedback</TableHead>
                    <TableHead className="w-28">Source</TableHead>
                    <TableHead className="w-32">Topic</TableHead>
                    <TableHead className="w-24">State</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {feedbacks.isPending ? (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <Spinner />
                      </TableCell>
                    </TableRow>
                  ) : filteredRows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <Empty>
                          <EmptyHeader>
                            <EmptyTitle>
                              Nothing matches these filters
                            </EmptyTitle>
                            <EmptyDescription>
                              Clear filters to return to the complete result
                              set.
                            </EmptyDescription>
                          </EmptyHeader>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSearch("")
                              setTopic("")
                              setSentiment("")
                              setAnalysisState("")
                              setPage(1)
                            }}
                          >
                            Clear filters
                          </Button>
                        </Empty>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredRows.map((row) => {
                      const ready = Boolean(row.ai_analysis)
                      return (
                        <TableRow
                          key={row.id}
                          className="cursor-pointer"
                          onClick={() => setDetailId(row.id)}
                        >
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <Checkbox
                              checked={selected.has(row.id)}
                              onCheckedChange={(checked) => {
                                setSelected((old) => {
                                  const next = new Set(old)
                                  if (checked) next.add(row.id)
                                  else next.delete(row.id)
                                  return next
                                })
                              }}
                              aria-label="Select feedback"
                            />
                          </TableCell>
                          <TableCell className="max-w-md break-words">
                            <span className="line-clamp-2 text-sm">
                              {row.feedback_text ?? "—"}
                            </span>
                            {row.pii_detected ? (
                              <Badge variant="outline" className="ml-2">
                                PII masked
                              </Badge>
                            ) : null}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {row.source}
                          </TableCell>
                          <TableCell className="text-sm break-words">
                            {row.ai_analysis?.uncategorized ? (
                              <Badge variant="outline">UNCATEGORIZED</Badge>
                            ) : (
                              (row.ai_analysis?.topics?.[0] ?? "—")
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant={ready ? "secondary" : "outline"}>
                              {ready ? "Ready" : "Pending"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
            <CardFooter className="flex-col items-stretch gap-3 border-t">
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
                <div className="text-sm text-muted-foreground">
                  {selected.size > 0 ? (
                    <>
                      {selected.size} selected · {selectedPending.length}{" "}
                      pending, {selectedReady} ready
                      <Button
                        size="sm"
                        variant="ghost"
                        className="ml-2"
                        onClick={() => setSelected(new Set())}
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
                      (selectedPending.length === 0 && !activeImportId)
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
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  Showing {total} of {feedbacks.data?.total ?? 0}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  <span className="font-mono">
                    {page} / {totalPages}
                  </span>
                  <Button
                    size="icon"
                    variant="ghost"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    aria-label="Next page"
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </div>
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
                    setSelected(new Set())
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
                    setSelected(new Set())
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

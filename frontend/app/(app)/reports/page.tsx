"use client"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import {
  Download,
  FileText,
  Pencil,
  Trash2,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AiBadge } from "@/components/ai/ai-badge"
import { PageHeader } from "@/components/page-header"
import { NextStepBar } from "@/components/journey/next-step-bar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import {
  useInsights,
  useDeleteInsight,
  useUpdateInsight,
} from "@/hooks/use-insights"
import { useProduct } from "@/hooks/use-product"
import { EvidenceCard } from "@/components/ai/evidence-card"
import { agentItemText, dedupeEvidence, humanizeAgentText } from "@/lib/evidence"
import type { InsightItem } from "@/lib/types"
import { INSIGHT_STATUS_TONE } from "@/lib/tone"
import { buildReportMarkdown, REPORT_STATUS_LABEL } from "@/lib/report-markdown"

function StatusBadge({ status }: { status: InsightItem["status"] }) {
  return (
    <Badge variant={INSIGHT_STATUS_TONE[status] ?? "secondary"}>
      {REPORT_STATUS_LABEL[status] ?? status}
    </Badge>
  )
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
  title: string
  status: InsightItem["status"]
  finding: string
  findingConfidence: number | null
  hypothesis: { statement: string | null; confidence: number | null } | null
  impact: string[]
  limitations: string[]
  evidence: { evidence_id: string; statement: string; source_tool?: string }[]
  runId: string | null
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl leading-snug">{title}</CardTitle>
        <CardAction>
          <StatusBadge status={status} />
        </CardAction>
        {runId ? (
          <CardDescription className="flex items-center gap-2 font-mono text-xs">
            Tổng hợp từ phản hồi
            <AiBadge />
          </CardDescription>
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-col gap-6">
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Kết luận
          </h3>
          <p className="font-heading text-lg leading-relaxed">{humanizeAgentText(finding)}</p>
          {findingConfidence != null ? (
            <p className="font-mono text-xs text-muted-foreground">
              Độ tin cậy {Math.round(findingConfidence * 100)}%
            </p>
          ) : null}
        </section>

        {hypothesis?.statement ? (
          <section className="flex flex-col gap-2 border-l-2 border-pollen pl-4">
            <h3 className="text-xs font-semibold tracking-wide text-warning uppercase">
              Giả thuyết — chưa xác nhận
            </h3>
            <p className="text-sm leading-relaxed">{humanizeAgentText(hypothesis.statement)}</p>
            {hypothesis.confidence != null ? (
              <p className="font-mono text-xs text-muted-foreground">
                Độ tin cậy {Math.round(hypothesis.confidence * 100)}%
              </p>
            ) : null}
          </section>
        ) : null}

        {impact.length > 0 ? (
          <section className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Ảnh hưởng
            </h3>
            <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
              {impact.map((i, idx) => (
                <li key={idx}>
                  {agentItemText(i)}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {limitations.length > 0 ? (
          <section className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Giới hạn
            </h3>
            <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted-foreground">
              {limitations.map((l, idx) => (
                <li key={idx}>
                  {agentItemText(l)}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Bằng chứng
          </h3>
          {evidence.length ? (
            <ul className="flex flex-col gap-2">
              {dedupeEvidence(evidence).map(({ item: e, repeats }, index) => (
                <li key={e.evidence_id}>
                  <EvidenceCard statement={e.statement} index={index + 1} repeats={repeats} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Chưa ghi nhận bằng chứng nào.
            </p>
          )}
        </section>
      </CardContent>
    </Card>
  )
}

function ReportEditDialog({
  report,
  open,
  onOpenChange,
}: {
  report: InsightItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const update = useUpdateInsight()
  // State khởi tạo từ prop; mount site dùng key={report.id} để re-seed form
  // mỗi lần mở report khác — không cần effect ghi đè state.
  const [title, setTitle] = useState(report?.title ?? "")
  const [finding, setFinding] = useState(report?.finding ?? "")

  if (!report) return null

  const save = () => {
    const body: { title?: string; finding?: string } = {}
    if (title.trim() && title !== report.title) body.title = title.trim()
    if (finding.trim() && finding !== report.finding)
      body.finding = finding.trim()
    if (Object.keys(body).length === 0) {
      onOpenChange(false)
      return
    }
    update.mutate(
      { id: report.id, body },
      {
        onSuccess: () => {
          toast.success("Đã lưu. Chỉnh sửa được ghi vào review history.")
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
          <DialogTitle>Sửa báo cáo</DialogTitle>
          <DialogDescription>
            Sửa title/finding sai do AI — mọi chỉnh sửa được log kèm reviewer.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="report-edit-title">Title</FieldLabel>
            <Input
              id="report-edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="report-edit-finding">Finding</FieldLabel>
            <Textarea
              id="report-edit-finding"
              value={finding}
              onChange={(e) => setFinding(e.target.value)}
              rows={4}
            />
          </Field>
        </FieldGroup>
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
  )
}

function ReportExportDialog({
  reports,
  productName,
  selectedId,
  total,
}: {
  reports: InsightItem[]
  productName?: string
  selectedId?: string
  total: number
}) {
  const defaultTitle = "Báo cáo vấn đề"
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState(defaultTitle)
  const [search, setSearch] = useState("")
  const [pickedIds, setPickedIds] = useState<Set<string>>(new Set())
  const options = reports.filter((report) =>
    report.title.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())
  )
  const picked = reports.filter((report) => pickedIds.has(report.id))

  function setDialogOpen(next: boolean) {
    if (next) {
      setTitle(defaultTitle)
      setSearch("")
      setPickedIds(new Set(selectedId ? [selectedId] : []))
    }
    setOpen(next)
  }

  function download() {
    if (!picked.length) return
    const now = new Date()
    const markdown = buildReportMarkdown(title.trim() || defaultTitle, productName, picked, now)
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }))
    const link = document.createElement("a")
    link.href = url
    link.download = "happynest-bao-cao-" + now.toISOString().slice(0, 10) + ".md"
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    setDialogOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setDialogOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={reports.length === 0}>
          <Download data-icon="inline-start" />
          Xuất Markdown
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-y-auto sm:max-w-xl">
        <DialogHeader className="pr-8">
          <DialogTitle>Tạo báo cáo Markdown</DialogTitle>
          <DialogDescription>
            Chọn một hoặc nhiều vấn đề của sản phẩm để gộp kết luận và bằng chứng vào một file .md.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup className="gap-3">
          <Field>
            <FieldLabel htmlFor="report-export-title">Tên báo cáo</FieldLabel>
            <Input
              id="report-export-title"
              value={title}
              maxLength={120}
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="report-export-search">Tìm vấn đề</FieldLabel>
            <Input
              id="report-export-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Tìm theo tiêu đề…"
            />
          </Field>
        </FieldGroup>
        <div className="flex max-h-64 min-h-20 flex-col gap-1 overflow-y-auto rounded-lg border p-2">
          {options.map((report) => (
            <label key={report.id} className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 hover:bg-accent/60">
              <Checkbox
                checked={pickedIds.has(report.id)}
                onCheckedChange={(checked) => {
                  setPickedIds((previous) => {
                    const next = new Set(previous)
                    if (checked === true) next.add(report.id)
                    else next.delete(report.id)
                    return next
                  })
                }}
              />
              <span className="min-w-0 flex-1 wrap-anywhere text-sm">{report.title}</span>
              <StatusBadge status={report.status} />
            </label>
          ))}
          {!options.length && (
            <p className="p-2 text-sm text-muted-foreground">Không có vấn đề khớp với từ khoá.</p>
          )}
        </div>
        <div className="flex flex-col gap-1 text-xs text-muted-foreground">
          <p aria-live="polite">Đã chọn {picked.length} vấn đề</p>
          {total > reports.length && <p>Danh sách gồm {reports.length} vấn đề được lưu gần nhất.</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDialogOpen(false)}>Huỷ</Button>
          <Button disabled={picked.length === 0} onClick={download}>
            <Download data-icon="inline-start" />
            Tải file .md
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Reports({
  initialRunId,
  initialReportId,
}: {
  initialRunId: string | null
  initialReportId: string | null
}) {
  const { product, productId } = useProduct()
  const insights = useInsights(productId)
  const reports = insights.data?.items
  const [selectedId, setSelectedId] = useState<string | null>(initialReportId)
  const [statusFilter, setStatusFilter] = useState("all")
  const [search, setSearch] = useState("")

  const items = useMemo(
    () =>
      (reports ?? []).filter(
        (i) =>
          (statusFilter === "all" || i.status === statusFilter) &&
          (!search || i.title.toLowerCase().includes(search.toLowerCase()))
      ),
    [reports, statusFilter, search]
  )

  const selected: InsightItem | undefined = useMemo(
    () => items.find((i) => i.id === (selectedId ?? items[0]?.id ?? null)),
    [items, selectedId]
  )

  const deleteInsight = useDeleteInsight()
  const [editingReport, setEditingReport] = useState<InsightItem | null>(null)
  const [confirmDeleteReport, setConfirmDeleteReport] = useState(false)
  // HAX G14 — the LLM can fail silently server-side; surface it here instead.


  return (
    <div className="flex flex-col gap-6">
      <NextStepBar />
      <PageHeader
        title="Báo cáo"
        description="Kết quả điều tra và bằng chứng. Duyệt kết luận ngay trong cuộc điều tra hoặc Chat."
        actions={
          <ReportExportDialog
            reports={reports ?? []}
            productName={product?.name}
            selectedId={selected?.id}
            total={insights.data?.total ?? 0}
          />
        }
      />

      {initialRunId ? <Alert><AlertTitle>Cuộc điều tra được duyệt tại chỗ</AlertTitle><AlertDescription>Tiếp tục trong màn điều tra để giữ nguyên câu hỏi và bằng chứng.</AlertDescription><Button size="sm" variant="outline" asChild><Link href={`/data-graph?run=${initialRunId}`}>Mở cuộc điều tra</Link></Button></Alert> : null}
      <div className="grid min-w-0 gap-6 lg:grid-cols-[260px_minmax(0,1fr)_300px]">
        {/* Reports list */}
        <Card size="sm" className="self-start">
          <CardHeader>
            <CardTitle>Danh sách báo cáo</CardTitle>
            <CardDescription>{insights.isPending ? "Đang tải báo cáo…" : `${items.length} trong sản phẩm này`}</CardDescription>
          </CardHeader>
          <CardContent className="gap-3">
            <Input
              placeholder="Tìm báo cáo…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Trạng thái" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Mọi trạng thái</SelectItem>
                <SelectItem value="pending">Chờ duyệt</SelectItem>
                <SelectItem value="investigating">Đang điều tra</SelectItem>
                <SelectItem value="approved">Đã duyệt</SelectItem>
                <SelectItem value="edited">Đã duyệt (có sửa)</SelectItem>
                <SelectItem value="rejected">Đã từ chối</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex flex-col gap-1">
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
                  <span className="block truncate font-heading text-sm">
                    {i.title}
                  </span>
                  <span className="mt-1 block">
                    <StatusBadge status={i.status} />
                  </span>
                </button>
              ))}
              {items.length === 0 && !insights.isPending && !insights.isError ? (
                <p className="px-2 text-sm text-muted-foreground">
                  No reports yet — ask a question in the Data Graph.
                </p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {/* Report body */}
        <div className="flex min-w-0 flex-col gap-4">
          {selected ? (
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
              {(selected.status === "pending" || selected.status === "investigating") && selected.run_id ? (
                <Button variant="outline" asChild><Link href={`/data-graph?run=${selected.run_id}`}>Tiếp tục và duyệt trong cuộc điều tra</Link></Button>
              ) : null}
                              <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={selected.status === "pending" || selected.status === "investigating"}
                    onClick={() => setEditingReport(selected)}
                  >
                    <Pencil data-icon="inline-start" />
                    Sửa báo cáo
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => setConfirmDeleteReport(true)}
                  >
                    <Trash2 data-icon="inline-start" />
                    Xoá báo cáo
                  </Button>
                </div>
              {selected.run_id ? <Button variant="outline" asChild><Link href={`/data-graph?run=${selected.run_id}`}>Xem cuộc điều tra và hành động</Link></Button> : null}
              {selected.status === "rejected" ? (
                <Alert>
                  <FileText className="size-4" />
                  <AlertTitle>Rejected reports remain visible</AlertTitle>
                  <AlertDescription>
                    The decision, time, reviewer, and revision stay in the
                    review history.
                  </AlertDescription>
                </Alert>
              ) : null}
            </>
          ) : insights.isPending ? (
            <Card><CardContent className="flex items-center gap-2 p-6"><Spinner />Đang tải báo cáo đã lưu…</CardContent></Card>
          ) : insights.isError ? (
            <Alert variant="destructive"><AlertTitle>Chưa tải được báo cáo</AlertTitle><AlertDescription>Dữ liệu vẫn được giữ trên máy chủ.</AlertDescription><Button variant="outline" size="sm" onClick={() => void insights.refetch()}>Tải lại</Button></Alert>
          ) : (
            <Card>
              <CardContent className="items-center p-8 text-center text-sm text-muted-foreground">
                Choose a report from the list, or ask a question in the{" "}
                <Link href="/data-graph" className="text-signal underline">
                  Data Graph
                </Link>
                .
              </CardContent>
            </Card>
          )}
        </div>

        {/* Review history rail */}
        <Card size="sm" className="self-start">
          <CardHeader>
            <CardTitle>Lịch sử duyệt</CardTitle>
          </CardHeader>
          <CardContent className="gap-3 text-sm">
            {items.length === 0 ? (
              <p className="text-muted-foreground">Chưa có quyết định nào.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {items.slice(0, 8).map((i) => (
                  <li
                    key={i.id}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="min-w-0 flex-1 truncate">{i.title}</span>
                    <StatusBadge status={i.status} />
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-muted-foreground">
              Mọi lần duyệt, sửa và từ chối đều được ghi lại kèm người duyệt.
            </p>
          </CardContent>
          {selected &&
          (selected.status === "approved" || selected.status === "edited") ? (
            <CardFooter>
              <Button variant="outline" className="w-full" asChild>
                <Link href={`/matrix?report=${selected.id}`}>Xem hành động</Link>
              </Button>
            </CardFooter>
          ) : null}
        </Card>
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
            <AlertDialogTitle>Xoá báo cáo?</AlertDialogTitle>
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
                e.preventDefault()
                if (!selected) return
                deleteInsight.mutate(selected.id, {
                  onSuccess: () => {
                    toast.success("Đã xoá báo cáo.")
                    setConfirmDeleteReport(false)
                    setSelectedId(null)
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
    </div>
  )
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <ReportsWithParams />
    </Suspense>
  )
}

function ReportsWithParams() {
  const params = useSearchParams()
  const { productId } = useProduct()
  return (
    <Reports
      key={productId}
      initialRunId={params.get("run")}
      initialReportId={params.get("report")}
    />
  )
}

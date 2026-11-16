"use client"
import { Suspense, useMemo, useState, type ReactNode } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import {
  ArrowRight,
  ChevronDown,
  Download,
  FileText,
  MoreHorizontal,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AiBadge } from "@/components/ai/ai-badge"
import { ConfidenceMeter } from "@/components/ai/confidence-meter"
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
  SelectGroup,
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
import { cn } from "@/lib/utils"

function StatusBadge({ status }: { status: InsightItem["status"] }) {
  return (
    <Badge variant={INSIGHT_STATUS_TONE[status] ?? "secondary"}>
      {REPORT_STATUS_LABEL[status] ?? status}
    </Badge>
  )
}

// ------------------------------------------------------------------ Report body

function shortReportDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
      {children}
    </h3>
  )
}

/**
 * Báo cáo đọc từ trên xuống như một bản ghi nghiên cứu (mẫu Elicit): kết luận
 * trước, chip trích dẫn ngay dưới nhận định trỏ tới đúng bằng chứng, phương pháp
 * và giới hạn gấp lại cho lúc cần đối chiếu.
 */
function ReportBody({
  report,
  actions,
}: {
  report: InsightItem
  actions: ReactNode
}) {
  const evidence = dedupeEvidence(report.evidence ?? [])
  const impact = (report.impact ?? []) as string[]
  const limitations = (report.limitations ?? []) as string[]
  const hypothesis = report.hypothesis
  const [focused, setFocused] = useState<number | null>(null)
  const [showMethod, setShowMethod] = useState(false)
  const methodCount = limitations.length + (hypothesis?.statement ? 1 : 0)

  const jumpTo = (index: number) => {
    setFocused(index)
    document
      .getElementById(`report-ev-${index}`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" })
  }

  return (
    <Card>
      <CardHeader className="gap-2">
        <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{shortReportDate(report.created_at)}</span>
          {report.run_id ? (
            <>
              <span aria-hidden>·</span>
              <span>Tổng hợp từ phản hồi</span>
              <AiBadge />
            </>
          ) : null}
        </p>
        <CardTitle className="font-heading text-2xl leading-snug">{report.title}</CardTitle>
        <CardAction>
          <StatusBadge status={report.status} />
        </CardAction>
        <div className="flex flex-wrap items-center gap-2 pt-1">{actions}</div>
      </CardHeader>

      <CardContent className="flex flex-col gap-6">
        <section className="flex flex-col gap-3 rounded-lg border border-leaf-line bg-leaf-soft/30 p-4">
          <SectionLabel>Kết luận</SectionLabel>
          <p className="font-heading text-lg leading-relaxed">{humanizeAgentText(report.finding)}</p>
          {evidence.length ? (
            <div className="flex flex-wrap items-center gap-1.5" aria-label="Kết luận dựa trên">
              <span className="text-xs text-muted-foreground">Nguồn</span>
              {evidence.map((_, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => jumpTo(index)}
                  aria-label={`Tới bằng chứng ${index + 1}`}
                  className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-sky-line bg-sky-soft/60 px-1.5 font-mono text-xs text-sky-ink transition-colors hover:bg-sky-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  {index + 1}
                </button>
              ))}
            </div>
          ) : null}
          <dl className="grid gap-x-6 gap-y-3 border-t border-leaf-line/60 pt-3 text-sm sm:grid-cols-3">
            <div className="flex flex-col gap-1">
              <dt className="text-xs text-muted-foreground">Độ tin cậy</dt>
              <dd>
                {report.finding_confidence != null ? (
                  <ConfidenceMeter value={report.finding_confidence} label="Ước lượng" className="gap-2" />
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-xs text-muted-foreground">Bằng chứng</dt>
              <dd className="font-mono">{evidence.length}</dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-xs text-muted-foreground">Ảnh hưởng ghi nhận</dt>
              <dd className="font-mono">{impact.length}</dd>
            </div>
          </dl>
        </section>

        {impact.length > 0 ? (
          <section className="flex flex-col gap-2">
            <SectionLabel>Ảnh hưởng</SectionLabel>
            <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
              {impact.map((i, idx) => (
                <li key={idx}>{agentItemText(i)}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="flex flex-col gap-3">
          <SectionLabel>Bằng chứng ({evidence.length})</SectionLabel>
          {evidence.length ? (
            <ol className="flex flex-col gap-2">
              {evidence.map(({ item: e, repeats }, index) => (
                <li key={e.evidence_id} id={`report-ev-${index}`} className="scroll-mt-24">
                  <EvidenceCard
                    statement={e.statement}
                    index={index + 1}
                    repeats={repeats}
                    className={cn(
                      "transition-shadow",
                      focused === index && "border-sky-line ring-2 ring-sky-soft"
                    )}
                  />
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">Chưa ghi nhận bằng chứng nào.</p>
          )}
        </section>

        <section className="flex flex-col gap-3 border-t pt-4">
          <Button
            variant="ghost"
            size="sm"
            className="self-start"
            aria-expanded={showMethod}
            onClick={() => setShowMethod(!showMethod)}
          >
            <ChevronDown
              data-icon="inline-start"
              className={cn("transition-transform", showMethod && "rotate-180")}
            />
            Phương pháp và giới hạn{methodCount ? ` (${methodCount})` : ""}
          </Button>
          {showMethod ? (
            <div className="flex flex-col gap-4 pl-1">
              <p className="text-sm text-muted-foreground">
                AI đọc các phản hồi đã ẩn thông tin cá nhân trong phạm vi được chọn, chạy các bước
                kiểm tra ở mục Bằng chứng rồi viết kết luận. Người duyệt quyết định giữ, sửa hay từ
                chối — mọi lần duyệt, sửa và từ chối đều được ghi lại kèm người duyệt.
              </p>
              {hypothesis?.statement ? (
                <div className="flex flex-col gap-1 border-l-2 border-pollen pl-4">
                  <p className="text-xs font-semibold tracking-wide text-warning uppercase">
                    Giả thuyết — chưa xác nhận
                  </p>
                  <p className="text-sm leading-relaxed">{humanizeAgentText(hypothesis.statement)}</p>
                  {hypothesis.confidence != null ? (
                    <p className="font-mono text-xs text-muted-foreground">
                      Độ tin cậy {Math.round(hypothesis.confidence * 100)}%
                    </p>
                  ) : null}
                </div>
              ) : null}
              {limitations.length > 0 ? (
                <div className="flex flex-col gap-1">
                  <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                    Giới hạn
                  </p>
                  <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted-foreground">
                    {limitations.map((l, idx) => (
                      <li key={idx}>{agentItemText(l)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
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
          toast.success("Đã lưu chỉnh sửa. Thay đổi được ghi vào lịch sử duyệt.")
          onOpenChange(false)
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Chưa lưu được thay đổi."
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
            Sửa tiêu đề hoặc kết luận AI viết chưa đúng. Mọi chỉnh sửa được ghi lại kèm người sửa.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="report-edit-title">Tiêu đề</FieldLabel>
            <Input
              id="report-edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="report-edit-finding">Kết luận</FieldLabel>
            <Textarea
              id="report-edit-finding"
              value={finding}
              onChange={(e) => setFinding(e.target.value)}
              rows={6}
            />
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Huỷ
          </Button>
          <Button onClick={save} disabled={update.isPending || !title.trim()}>
            {update.isPending ? <Spinner data-icon="inline-start" /> : null}
            Lưu chỉnh sửa
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

  const selectedOpen =
    selected?.status === "pending" || selected?.status === "investigating"
  const selectedApproved =
    selected?.status === "approved" || selected?.status === "edited"

  const reportActions = selected ? (
    <>
      {selectedApproved ? (
        <Button size="sm" asChild>
          <Link href={`/matrix?report=${selected.id}`}>
            Xem hành động
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      ) : null}
      {selectedOpen && selected.run_id ? (
        <Button size="sm" asChild>
          <Link href={`/data-graph?run=${selected.run_id}`}>Duyệt trong cuộc điều tra</Link>
        </Button>
      ) : null}
      {selected.run_id && !selectedOpen ? (
        <Button size="sm" variant="outline" asChild>
          <Link href={`/data-graph?run=${selected.run_id}`}>Mở cuộc điều tra</Link>
        </Button>
      ) : null}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="icon-sm" variant="ghost" aria-label="Thao tác khác với báo cáo">
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuGroup>
            <DropdownMenuItem
              disabled={selectedOpen}
              onSelect={() => setEditingReport(selected)}
            >
              <Pencil />
              Sửa báo cáo
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => setConfirmDeleteReport(true)}
            >
              <Trash2 />
              Xoá báo cáo
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  ) : null

  return (
    <div className="flex flex-col gap-6">
      <NextStepBar />
      <PageHeader
        title="Báo cáo"
        description="Kết luận đã điều tra, kèm bằng chứng và quyết định duyệt."
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
      <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]">
        {/* Reports list */}
        <Card size="sm" className="lg:sticky lg:top-20">
          <CardHeader>
            <CardTitle>Danh sách báo cáo</CardTitle>
            <CardDescription>{insights.isPending ? "Đang tải báo cáo…" : `${items.length} trong sản phẩm này`}</CardDescription>
          </CardHeader>
          <CardContent className="gap-3">
            <Input
              aria-label="Tìm báo cáo"
              placeholder="Tìm báo cáo…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label="Lọc theo trạng thái">
                <SelectValue placeholder="Trạng thái" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Mọi trạng thái</SelectItem>
                  <SelectItem value="pending">Chờ duyệt</SelectItem>
                  <SelectItem value="investigating">Đang điều tra</SelectItem>
                  <SelectItem value="approved">Đã duyệt</SelectItem>
                  <SelectItem value="edited">Đã duyệt (có sửa)</SelectItem>
                  <SelectItem value="rejected">Đã từ chối</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
            <div className="-mx-1 flex max-h-[55vh] flex-col gap-1 overflow-y-auto px-1">
              {items.map((i) => {
                const active = selected?.id === i.id
                return (
                  <button
                    key={i.id}
                    type="button"
                    aria-current={active ? "true" : undefined}
                    onClick={() => setSelectedId(i.id)}
                    className={cn(
                      "flex w-full flex-col gap-1.5 rounded-lg border-l-2 px-3 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-ring",
                      active
                        ? "border-l-lichen bg-accent"
                        : "border-l-transparent hover:bg-accent/60"
                    )}
                  >
                    <span className="line-clamp-2 font-heading text-sm leading-snug">
                      {i.title}
                    </span>
                    <span className="flex items-center justify-between gap-2">
                      <StatusBadge status={i.status} />
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {shortReportDate(i.created_at)}
                      </span>
                    </span>
                  </button>
                )
              })}
              {items.length === 0 && !insights.isPending && !insights.isError ? (
                <p className="px-2 text-sm text-muted-foreground">
                  {search || statusFilter !== "all"
                    ? "Không có báo cáo khớp bộ lọc."
                    : "Chưa có báo cáo. Hỏi AI trong màn Điều tra để tạo báo cáo đầu tiên."}
                </p>
              ) : null}
            </div>
          </CardContent>
          <CardFooter>
            <p className="text-xs text-muted-foreground">
              Mọi lần duyệt, sửa và từ chối đều được ghi lại kèm người duyệt.
            </p>
          </CardFooter>
        </Card>

        {/* Report body */}
        <div className="flex min-w-0 flex-col gap-4">
          {selected ? (
            <>
              {selected.status === "rejected" ? (
                <Alert>
                  <FileText />
                  <AlertTitle>Báo cáo đã bị từ chối</AlertTitle>
                  <AlertDescription>
                    Báo cáo vẫn được giữ để đối chiếu. Quyết định, thời điểm và người duyệt nằm trong lịch sử duyệt.
                  </AlertDescription>
                </Alert>
              ) : null}
              <ReportBody key={selected.id} report={selected} actions={reportActions} />
            </>
          ) : insights.isPending ? (
            <Card><CardContent className="flex items-center gap-2 p-6"><Spinner />Đang tải báo cáo đã lưu…</CardContent></Card>
          ) : insights.isError ? (
            <Alert variant="destructive"><AlertTitle>Chưa tải được báo cáo</AlertTitle><AlertDescription>Dữ liệu vẫn được giữ trên máy chủ.</AlertDescription><Button variant="outline" size="sm" onClick={() => void insights.refetch()}>Tải lại</Button></Alert>
          ) : (
            <Empty className="border">
              <EmptyHeader>
                <EmptyTitle>Chưa có báo cáo để đọc</EmptyTitle>
                <EmptyDescription>
                  Báo cáo xuất hiện sau khi bạn hỏi AI và duyệt kết luận trong màn Điều tra.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button asChild>
                  <Link href="/data-graph?ask=1">Hỏi AI</Link>
                </Button>
              </EmptyContent>
            </Empty>
          )}
        </div>
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
              Báo cáo “{selected?.title}” và toàn bộ hành động liên quan sẽ bị xoá
              vĩnh viễn, không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
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
                      err instanceof Error ? err.message : "Chưa xoá được báo cáo."
                    ),
                })
              }}
            >
              {deleteInsight.isPending ? <Spinner data-icon="inline-start" /> : null}
              Xoá vĩnh viễn
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

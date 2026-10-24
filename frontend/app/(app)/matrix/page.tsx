"use client"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
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
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AiBadge } from "@/components/ai/ai-badge"
import { ActionDecisionSupport } from "@/components/actions/action-decision-support"
import { PageHeader } from "@/components/page-header"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useInsights } from "@/hooks/use-insights"
import { useActions, useAddAction, useUpdateAction } from "@/hooks/use-actions"
import { useProduct } from "@/hooks/use-product"
import { departmentLabel } from "@/lib/departments"
import { useAppLang } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { effectiveScores, QUADRANT_LABEL, quadrantOf } from "@/lib/matrix"
import type { ActionItem, BusinessFunction, Quadrant } from "@/lib/types"

const BUSINESS_FUNCTIONS: { value: BusinessFunction; label: string }[] = [
  { value: "ENGINEERING", label: "Engineering" },
  { value: "SUPPORT", label: "Support" },
  { value: "DESIGN", label: "Design" },
  { value: "MARKETING", label: "Marketing" },
  { value: "LEGAL", label: "Legal" },
  { value: "FINANCE", label: "Finance" },
  { value: "OPERATION", label: "Operations" },
  { value: "SALES", label: "Sales" },
]

const DEPARTMENT_COLOR: Record<BusinessFunction, string> = {
  ENGINEERING: "text-department-engineering",
  SUPPORT: "text-department-support",
  DESIGN: "text-department-design",
  MARKETING: "text-department-marketing",
  LEGAL: "text-department-legal",
  FINANCE: "text-department-finance",
  OPERATION: "text-department-operations",
  SALES: "text-department-sales",
}

type Draft = {
  impact: number
  effort: number
  urgency: number
  reason: string
}

function draftFrom(action: ActionItem): Draft {
  const eff = effectiveScores(action)
  return {
    impact: eff.impact,
    effort: eff.effort,
    urgency: eff.urgency,
    reason: "",
  }
}

function toQuadrantLabel(q: Quadrant): string {
  return QUADRANT_LABEL[q]
}

// ------------------------------------------------------------------ D02 drawer

function ActionDrawer({
  action,
  initialDraft,
  onClose,
}: {
  action: ActionItem | null
  initialDraft?: Draft | null
  onClose: () => void
}) {
  const update = useUpdateAction()
  // Initialized per session — the parent remounts the drawer via `key`.
  const [draft, setDraft] = useState<Draft | null>(() =>
    action ? (initialDraft ?? draftFrom(action)) : null
  )

  const dirty =
    action && draft
      ? draft.impact !== effectiveScores(action).impact ||
        draft.effort !== effectiveScores(action).effort ||
        draft.urgency !== effectiveScores(action).urgency ||
        draft.reason.trim() !== ""
      : false

  const [confirmDiscard, setConfirmDiscard] = useState(false)

  const requestClose = () => {
    if (dirty) setConfirmDiscard(true)
    else onClose()
  }

  const patch = (body: Record<string, unknown>, successMsg: string) => {
    if (!action) return
    update.mutate(
      { actionId: action.id, body },
      {
        onSuccess: () => {
          toast.success(successMsg)
          onClose()
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Update failed"),
      }
    )
  }

  if (!action || !draft) {
    return (
      <Sheet open={false} onOpenChange={() => {}}>
        <SheetContent />
      </Sheet>
    )
  }

  const previewQuadrant = quadrantOf(draft.impact, draft.effort)
  const originalQuadrant = quadrantOf(
    effectiveScores(action).impact,
    effectiveScores(action).effort
  )

  return (
    <Sheet open onOpenChange={(open) => !open && requestClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="break-words">
            {action.recommendation}
          </SheetTitle>
          <SheetDescription>
            {departmentLabel(action.function)} · {action.status}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-6 px-4 pb-8">
          <section className="flex flex-col gap-1">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              What
            </h3>
            <p className="text-sm">{action.recommendation}</p>
            {action.rationale ? (
              <p className="text-sm text-muted-foreground">
                {action.rationale}
              </p>
            ) : null}
          </section>

          <section className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Why
            </h3>
            <p className="text-sm">
              Supported by the reviewed finding.{" "}
              <Link
                className="text-signal underline"
                href={`/reports?report=${action.insight_id}`}
              >
                Open report
              </Link>
            </p>
          </section>

          <ActionDecisionSupport action={action} />

          <section>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs tracking-wide text-muted-foreground uppercase">
                  <th className="pb-2 font-medium">AI estimate</th>
                  <th className="pb-2 font-medium">Your decision</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {(
                  [
                    ["Impact", "impact"],
                    ["Effort", "effort"],
                    ["Urgency", "urgency"],
                  ] as const
                ).map(([label, key]) => (
                  <tr key={key} className="border-t">
                    <td className="py-2">{action[key]}</td>
                    <td className="py-2">
                      <Input
                        type="number"
                        min={1}
                        max={10}
                        className="h-8 w-20 font-mono"
                        value={draft[key]}
                        onChange={(e) => {
                          const v = Number(e.target.value)
                          if (v >= 1 && v <= 10)
                            setDraft({ ...draft, [key]: v })
                        }}
                        aria-label={`${label} decision (1-10)`}
                      />
                    </td>
                  </tr>
                ))}
                <tr className="border-t">
                  <td className="py-2">{action.confidence.toFixed(2)}</td>
                  <td className="py-2 text-muted-foreground">—</td>
                </tr>
              </tbody>
            </table>
            <AiBadge className="mt-2" />
            {previewQuadrant !== originalQuadrant ? (
              <p className="mt-2 text-xs">
                Preview: moves to{" "}
                <strong>{toQuadrantLabel(previewQuadrant)}</strong> (from{" "}
                {toQuadrantLabel(originalQuadrant)}). Nothing changes until Save
                or Accept.
              </p>
            ) : null}
          </section>

          <Field>
            <FieldLabel htmlFor="override-reason">
              Reason for changes
            </FieldLabel>
            <Textarea
              id="override-reason"
              rows={2}
              placeholder="Why did you adjust the AI estimates?"
              value={draft.reason}
              onChange={(e) => setDraft({ ...draft, reason: e.target.value })}
            />
          </Field>

          <Alert>
            <AlertDescription>
              G3 — You decide the final priority. Saving an edit never implies
              acceptance.
            </AlertDescription>
          </Alert>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="outline"
              disabled={update.isPending}
              onClick={() =>
                patch(
                  { status: "rejected" },
                  "Action rejected — kept in history."
                )
              }
            >
              Reject
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={update.isPending || !dirty}
                onClick={() =>
                  patch(
                    {
                      impact: draft.impact,
                      effort: draft.effort,
                      urgency: draft.urgency,
                      override_reason: draft.reason || undefined,
                    },
                    "Edits saved — awaiting decision."
                  )
                }
              >
                Save edits
              </Button>
              <Button
                disabled={update.isPending}
                onClick={() =>
                  patch(
                    {
                      status: "accepted",
                      impact: draft.impact,
                      effort: draft.effort,
                      urgency: draft.urgency,
                      override_reason: draft.reason || undefined,
                    },
                    "Action accepted."
                  )
                }
              >
                Accept action
              </Button>
            </div>
          </div>
        </div>

        <AlertDialog open={confirmDiscard} onOpenChange={setConfirmDiscard}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Discard your changes?</AlertDialogTitle>
              <AlertDialogDescription>
                Your unsaved edits to this action will be lost.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep editing</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  setConfirmDiscard(false)
                  onClose()
                }}
              >
                Discard changes
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SheetContent>
    </Sheet>
  )
}

// ------------------------------------------------------------------ Matrix point

function MatrixPoint({
  action,
  onOpen,
}: {
  action: ActionItem
  onOpen: () => void
}) {
  const lang = useAppLang()
  const eff = effectiveScores(action)
  const scoreLabel = lang === "vi"
    ? `Tác động ${eff.impact}/10 · Nỗ lực ${eff.effort}/10`
    : `Impact ${eff.impact}/10 · Effort ${eff.effort}/10`
  const statusLabel = {
    proposed: lang === "vi" ? "Đề xuất" : "Proposed",
    edited: lang === "vi" ? "Đã chỉnh sửa" : "Edited",
    accepted: lang === "vi" ? "Đã chấp nhận" : "Accepted",
    rejected: lang === "vi" ? "Đã từ chối" : "Rejected",
  }[action.status]
  const left = Math.min(94, Math.max(6, (eff.effort / 10) * 100))
  const bottom = Math.min(94, Math.max(6, (eff.impact / 10) * 100))
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          draggable
          onDragStart={(e) => e.dataTransfer.setData("text/action-id", action.id)}
          onClick={onOpen}
          aria-label={`${action.recommendation} — ${departmentLabel(action.function)} — ${scoreLabel} — ${statusLabel}`}
          className={cn(
            "absolute flex size-6 -translate-x-1/2 translate-y-1/2 cursor-grab items-center justify-center rounded-full hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:cursor-grabbing",
            DEPARTMENT_COLOR[action.function]
          )}
          style={{ left: `${left}%`, bottom: `${bottom}%` }}
        >
          <span aria-hidden="true" className={cn(
            "size-3 rounded-full border-2 border-current",
            action.status !== "rejected" && "bg-current"
          )} />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-80 flex-col items-start gap-1" sideOffset={8}>
        <p className="break-words font-medium">{action.recommendation}</p>
        <p>{departmentLabel(action.function)} · {statusLabel}</p>
        <p>{scoreLabel}</p>
      </TooltipContent>
    </Tooltip>
  )
}

// ------------------------------------------------------------------ Add action dialog

function AddActionDialog({
  insightId,
  open,
  onOpenChange,
}: {
  insightId: string
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  const add = useAddAction()
  const [fn, setFn] = useState<BusinessFunction>("ENGINEERING")
  const [recommendation, setRecommendation] = useState("")
  const [impact, setImpact] = useState(5)
  const [effort, setEffort] = useState(5)
  const [urgency, setUrgency] = useState(5)

  const submit = () => {
    add.mutate(
      {
        insightId,
        body: { function: fn, recommendation, impact, effort, urgency },
      },
      {
        onSuccess: () => {
          toast.success("Action added and accepted.")
          onOpenChange(false)
          setRecommendation("")
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Could not add action"
          ),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add manual action</DialogTitle>
          <DialogDescription>
            Requires a department, recommendation, and scores. The final button
            makes the acceptance decision explicit.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel>Department</FieldLabel>
            <Select
              value={fn}
              onValueChange={(v) => setFn(v as BusinessFunction)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BUSINESS_FUNCTIONS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel>Recommendation</FieldLabel>
            <Textarea
              rows={2}
              value={recommendation}
              onChange={(e) => setRecommendation(e.target.value)}
              placeholder="What should be done?"
            />
          </Field>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["Impact", impact, setImpact],
                ["Effort", effort, setEffort],
                ["Urgency", urgency, setUrgency],
              ] as const
            ).map(([label, value, set]) => (
              <Field key={label}>
                <FieldLabel>{label}</FieldLabel>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  className="font-mono"
                  value={value}
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    if (v >= 1 && v <= 10) set(v)
                  }}
                />
              </Field>
            ))}
          </div>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={recommendation.trim().length < 3 || add.isPending}
            onClick={submit}
          >
            Add and accept action
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ------------------------------------------------------------------ Screen

function Matrix({ initialReportId }: { initialReportId: string | null }) {
  const lang = useAppLang()
  const { product } = useProduct()
  const insights = useInsights()
  const [reportId, setReportId] = useState<string | null>(initialReportId)
  const [department, setDepartment] = useState("all")
  const [statusFilter, setStatusFilter] = useState("active")
  const [openActionId, setOpenActionId] = useState<string | null>(null)
  const [dropPreview, setDropPreview] = useState<{
    actionId: string
    draft: Draft
  } | null>(null)
  const [addOpen, setAddOpen] = useState(false)

  const eligibleReports = useMemo(
    () =>
      (insights.data?.items ?? []).filter(
        (i) =>
          i.status === "approved" ||
          i.status === "edited" ||
          i.status === "pending" ||
          i.status === "investigating"
      ),
    [insights.data]
  )

  // Derived selection: falls back to the first eligible report.
  const effectiveReportId = reportId ?? eligibleReports[0]?.id ?? null

  const actions = useActions(effectiveReportId)
  const allItems = useMemo(() => actions.data?.items ?? [], [actions.data])

  const items = useMemo(() => {
    return allItems.filter((a) => {
      if (
        department !== "all" &&
        departmentLabel(a.function).toLowerCase() !== department
      )
        return false
      if (statusFilter === "active") return a.status !== "rejected"
      if (statusFilter === "rejected") return a.status === "rejected"
      if (statusFilter === "accepted") return a.status === "accepted"
      return true
    })
  }, [allItems, department, statusFilter])

  const openAction = items.find((a) => a.id === openActionId) ?? null
  const matrix = actions.data?.matrix

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={product?.name ?? "Priority Matrix"}
        description="Ưu tiên hành động theo tác động và nỗ lực — giữ khuyến nghị gốc của hệ thống khi ghi đè."
        actions={
          <Button
            disabled={!effectiveReportId}
            onClick={() => setAddOpen(true)}
          >
            + Add action
          </Button>
        }
      />

      <Card size="sm">
        <CardContent className="flex-row flex-wrap items-center gap-2">
          <Select value={effectiveReportId ?? ""} onValueChange={setReportId}>
            <SelectTrigger className="w-72">
              <SelectValue placeholder="Report: choose one" />
            </SelectTrigger>
            <SelectContent>
              {eligibleReports.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  Report: {r.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={department} onValueChange={setDepartment}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Department: All</SelectItem>
              {BUSINESS_FUNCTIONS.map((f) => (
                <SelectItem key={f.value} value={f.label.toLowerCase()}>
                  Department: {f.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Status: Active</SelectItem>
              <SelectItem value="accepted">Status: Accepted</SelectItem>
              <SelectItem value="rejected">Status: Rejected</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {!effectiveReportId ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>No reviewed report yet</EmptyTitle>
            <EmptyDescription>
              Approve a finding in Reports first — actions are generated from
              reviewed findings only.
            </EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link href="/reports">Open Reports</Link>
          </Button>
        </Empty>
      ) : actions.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load actions</AlertTitle>
          <AlertDescription>
            {actions.error.message} — the actions are safe on the server.
          </AlertDescription>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 w-fit"
            onClick={() => void actions.refetch()}
          >
            Retry
          </Button>
        </Alert>
      ) : actions.isPending ? (
        <Spinner />
      ) : items.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>No actions here</EmptyTitle>
            <EmptyDescription>
              Generate actions from the approved report, or add one manually.
            </EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link href={`/reports?report=${effectiveReportId}`}>
              Open source report
            </Link>
          </Button>
        </Empty>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Ma trận ưu tiên</CardTitle>
            <CardDescription>
              {lang === "vi"
                ? "Mỗi chấm là một hành động; màu thể hiện phòng ban. Rê chuột để xem nội dung, bấm để mở chi tiết hoặc kéo thả để điều chỉnh ưu tiên."
                : "Each dot is an action; its color shows the department. Hover to read, click for details, or drag to adjust priority."}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex justify-between px-1 text-xs text-muted-foreground">
              <span>Expected customer impact — High ↑</span>
              <span>Effort → High</span>
            </div>
            <div
              className="relative h-[480px] overflow-hidden rounded-lg border bg-card"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const id = e.dataTransfer.getData("text/action-id")
                const dropped = allItems.find((a) => a.id === id)
                if (!dropped || !e.currentTarget) return
                const rect = e.currentTarget.getBoundingClientRect()
                const x = (e.clientX - rect.left) / rect.width
                const y = (e.clientY - rect.top) / rect.height
                const effort = Math.min(10, Math.max(1, Math.round(x * 10)))
                const impact = Math.min(
                  10,
                  Math.max(1, Math.round((1 - y) * 10))
                )
                setDropPreview({
                  actionId: id,
                  draft: {
                    impact,
                    effort,
                    urgency: effectiveScores(dropped).urgency,
                    reason: "",
                  },
                })
                setOpenActionId(id)
              }}
            >
              {/* quadrant midlines */}
              <div className="absolute top-0 left-1/2 h-full w-px bg-border" />
              <div className="absolute top-1/2 left-0 h-px w-full bg-border" />
              {/* quadrant labels */}
              {(
                [
                  ["Quick wins", "left-3 top-3"],
                  ["Strategic investments", "right-3 top-3"],
                  ["Low priority", "left-3 bottom-3"],
                  ["Reconsider", "right-3 bottom-3"],
                ] as const
              ).map(([label, pos]) => (
                <span
                  key={label}
                  className={`absolute ${pos} text-xs font-semibold tracking-wide text-muted-foreground/70 uppercase`}
                >
                  {label}
                </span>
              ))}
              {items.map((a) => (
                <MatrixPoint
                  key={a.id}
                  action={a}
                  onOpen={() => setOpenActionId(a.id)}
                />
              ))}
              {matrix ? null : null}
            </div>
            <div className="flex justify-between px-1 text-xs text-muted-foreground">
              <span>Low effort</span>
              <span>High effort</span>
            </div>
            <ul
              aria-label={lang === "vi" ? "Chú giải phòng ban" : "Department legend"}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground"
            >
              {BUSINESS_FUNCTIONS.filter((f) => items.some((a) => a.function === f.value)).map((f) => (
                <li key={f.value} className="flex items-center gap-1.5">
                  <span aria-hidden="true" className={cn("size-2.5 shrink-0 rounded-full bg-current", DEPARTMENT_COLOR[f.value])} />
                  {f.label}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter className="flex-wrap justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              Points are actions. Priority also considers urgency and
              confidence.
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href={`/reports?report=${effectiveReportId}`}>
                  View source report
                </Link>
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/stakeholders?report=${effectiveReportId}`}>
                  View by department
                </Link>
              </Button>
            </div>
          </CardFooter>
        </Card>
      )}

      <ActionDrawer
        key={openActionId ?? "none"}
        action={openAction}
        initialDraft={
          dropPreview?.actionId === openActionId ? dropPreview.draft : null
        }
        onClose={() => {
          setOpenActionId(null)
          setDropPreview(null)
        }}
      />
      {effectiveReportId ? (
        <AddActionDialog
          insightId={effectiveReportId}
          open={addOpen}
          onOpenChange={setAddOpen}
        />
      ) : null}
    </div>
  )
}

export default function MatrixPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <MatrixWithParams />
    </Suspense>
  )
}

function MatrixWithParams() {
  const params = useSearchParams()
  return <Matrix initialReportId={params.get("report")} />
}

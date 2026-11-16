"use client"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { LayoutGrid, Plus, Rows3 } from "lucide-react"
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
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AiBadge } from "@/components/ai/ai-badge"
import { ActionDecisionSupport } from "@/components/actions/action-decision-support"
import { PageHeader } from "@/components/page-header"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useInsights } from "@/hooks/use-insights"
import {
  useActions,
  useAddAction,
  useGenerateActions,
  useUpdateAction,
} from "@/hooks/use-actions"
import { departmentLabel } from "@/lib/departments"
import { useAppLang, useT } from "@/lib/i18n"
import { NextStepBar } from "@/components/journey/next-step-bar"
import { cn } from "@/lib/utils"
import { effectiveScores, quadrantOf } from "@/lib/matrix"
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

const QUADRANT_VI: Record<Quadrant, string> = {
  quick_wins: "Làm ngay",
  strategic_investments: "Đầu tư chiến lược",
  low_priority: "Ưu tiên thấp",
  reconsider: "Cân nhắc lại",
}

const ACTION_STATUS_VI: Record<string, string> = {
  proposed: "Đề xuất",
  edited: "Đã chỉnh",
  accepted: "Đã nhận",
  rejected: "Đã từ chối",
}

/// ------------------------------------------------------------------ Quadrant preview

const QUADRANT_TINT: Record<Quadrant, string> = {
  quick_wins: "bg-leaf-soft/70",
  strategic_investments: "bg-sky-soft/70",
  low_priority: "bg-muted/60",
  reconsider: "bg-coral-soft/60",
}

/** Ma trận thu nhỏ trong ngăn chi tiết: chấm rỗng = vị trí đang lưu, chấm đặc =
 * vị trí theo điểm bạn vừa chỉnh. Người dùng thấy hành động sẽ sang ô nào
 * TRƯỚC khi lưu (khoảng trống chưa có mẫu tham chiếu nào phủ). */
function QuadrantPreview({
  from,
  to,
  colorClass,
}: {
  from: { impact: number; effort: number }
  to: { impact: number; effort: number }
  colorClass: string
}) {
  const pos = (s: { impact: number; effort: number }) => ({
    left: `${Math.min(92, Math.max(8, (s.effort / 10) * 100))}%`,
    bottom: `${Math.min(92, Math.max(8, (s.impact / 10) * 100))}%`,
  })
  const moved = from.impact !== to.impact || from.effort !== to.effort
  return (
    <div className="flex items-end gap-3">
      <div
        className={cn("relative grid size-32 shrink-0 grid-cols-2 grid-rows-2 overflow-hidden rounded-md border", colorClass)}
        role="img"
        aria-label={`Vị trí trên ma trận: ${QUADRANT_VI[quadrantOf(to.impact, to.effort)]}`}
      >
        {(["quick_wins", "strategic_investments", "low_priority", "reconsider"] as const).map((q) => (
          <div
            key={q}
            className={cn(
              QUADRANT_TINT[q],
              quadrantOf(to.impact, to.effort) === q && "outline-2 -outline-offset-2 outline-current/40"
            )}
          />
        ))}
        {moved ? (
          <span
            aria-hidden="true"
            className="absolute size-3 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-dashed border-current"
            style={pos(from)}
          />
        ) : null}
        <span
          aria-hidden="true"
          className="absolute size-3 -translate-x-1/2 translate-y-1/2 rounded-full bg-current ring-2 ring-card transition-[left,bottom] duration-300 motion-reduce:transition-none"
          style={pos(to)}
        />
      </div>
      <div className="flex flex-col gap-1 text-xs text-muted-foreground">
        <span>↑ Tác động · Nỗ lực →</span>
        {moved ? (
          <span className="text-foreground">
            {quadrantOf(from.impact, from.effort) === quadrantOf(to.impact, to.effort) ? (
              <>Vẫn ở <strong>{QUADRANT_VI[quadrantOf(to.impact, to.effort)]}</strong></>
            ) : (
              <>
                {QUADRANT_VI[quadrantOf(from.impact, from.effort)]} →{" "}
                <strong>{QUADRANT_VI[quadrantOf(to.impact, to.effort)]}</strong>
              </>
            )}
          </span>
        ) : (
          <span className="text-foreground">
            Đang ở <strong>{QUADRANT_VI[quadrantOf(to.impact, to.effort)]}</strong>
          </span>
        )}
        <span>Chưa có gì thay đổi cho tới khi bạn lưu hoặc nhận.</span>
      </div>
    </div>
  )
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
          toast.error(err instanceof Error ? err.message : "Chưa lưu được. Nội dung chỉnh sửa vẫn được giữ."),
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

  const saved = effectiveScores(action)

  return (
    <Sheet open onOpenChange={(open) => !open && requestClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <p className={cn("flex items-center gap-1.5 text-xs", DEPARTMENT_COLOR[action.function])}>
            <span aria-hidden="true" className="size-2 rounded-full bg-current" />
            <span className="text-muted-foreground">
              {departmentLabel(action.function)} · {ACTION_STATUS_VI[action.status] ?? action.status}
            </span>
          </p>
          <SheetTitle className="font-heading text-lg leading-snug break-words">
            {action.recommendation}
          </SheetTitle>
          {action.rationale ? (
            <SheetDescription>{action.rationale}</SheetDescription>
          ) : null}
        </SheetHeader>

        <div className="flex flex-col gap-6 px-4 pb-8">
          <section className="flex flex-col gap-3 rounded-lg border p-3">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Điểm ưu tiên
            </h3>
            <QuadrantPreview
              from={saved}
              to={{ impact: draft.impact, effort: draft.effort }}
              colorClass={DEPARTMENT_COLOR[action.function]}
            />
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Tiêu chí</th>
                  <th className="pb-2 font-medium">AI ước lượng</th>
                  <th className="pb-2 font-medium">Quyết định của bạn</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Tác động", "impact"],
                    ["Nỗ lực", "effort"],
                    ["Khẩn cấp", "urgency"],
                  ] as const
                ).map(([label, key]) => (
                  <tr key={key} className="border-t">
                    <td className="py-2">{label}</td>
                    <td className="py-2 font-mono">{action[key]}</td>
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
                        aria-label={`${label}: quyết định của bạn (1–10)`}
                      />
                    </td>
                  </tr>
                ))}
                <tr className="border-t">
                  <td className="py-2">Độ tin cậy</td>
                  <td className="py-2 font-mono">{action.confidence.toFixed(2)}</td>
                  <td className="py-2 text-muted-foreground">—</td>
                </tr>
              </tbody>
            </table>
            <AiBadge />
          </section>

          <Field>
            <FieldLabel htmlFor="override-reason">
              Lý do thay đổi
            </FieldLabel>
            <Textarea
              id="override-reason"
              rows={2}
              placeholder="Vì sao bạn chỉnh ước lượng của AI?"
              value={draft.reason}
              onChange={(e) => setDraft({ ...draft, reason: e.target.value })}
            />
          </Field>

          <ActionDecisionSupport action={action} />

          <section className="flex flex-col gap-1">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Căn cứ
            </h3>
            <p className="text-sm">
              Dựa trên kết luận đã được duyệt.{" "}
              <Link
                className="text-signal underline"
                href={`/reports?report=${action.insight_id}`}
              >
                Mở báo cáo
              </Link>
            </p>
          </section>
        </div>

        <SheetFooter className="sticky bottom-0 border-t bg-popover">
          <p className="text-xs text-muted-foreground">
            Bạn quyết định ưu tiên cuối cùng. Lưu chỉnh sửa chưa có nghĩa là đã nhận hành động.
          </p>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="ghost"
              disabled={update.isPending || action.status === "rejected"}
              onClick={() =>
                patch(
                  { status: "rejected" },
                  "Đã từ chối hành động — vẫn giữ trong lịch sử."
                )
              }
            >
              Từ chối
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
                    "Đã lưu chỉnh sửa — chờ bạn quyết định."
                  )
                }
              >
                Lưu chỉnh sửa
              </Button>
              <Button
                disabled={update.isPending || (action.status === "accepted" && !dirty)}
                onClick={() =>
                  patch(
                    {
                      status: "accepted",
                      impact: draft.impact,
                      effort: draft.effort,
                      urgency: draft.urgency,
                      override_reason: draft.reason || undefined,
                    },
                    "Đã nhận hành động."
                  )
                }
              >
                {update.isPending ? <Spinner data-icon="inline-start" /> : null}
                Nhận hành động
              </Button>
            </div>
          </div>
        </SheetFooter>

        <AlertDialog open={confirmDiscard} onOpenChange={setConfirmDiscard}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Bỏ các chỉnh sửa?</AlertDialogTitle>
              <AlertDialogDescription>
                Điểm và lý do bạn vừa nhập cho hành động này chưa được lưu.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Tiếp tục chỉnh</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  setConfirmDiscard(false)
                  onClose()
                }}
              >
                Bỏ chỉnh sửa
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
  highlighted,
  dimmed,
  onOpen,
  onHover,
}: {
  action: ActionItem
  highlighted: boolean
  dimmed: boolean
  onOpen: () => void
  onHover: (id: string | null) => void
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
  const pending = action.status === "proposed" || action.status === "edited"
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          draggable
          onDragStart={(e) => e.dataTransfer.setData("text/action-id", action.id)}
          onClick={onOpen}
          onMouseEnter={() => onHover(action.id)}
          onMouseLeave={() => onHover(null)}
          onFocus={() => onHover(action.id)}
          onBlur={() => onHover(null)}
          aria-label={`${action.recommendation} — ${departmentLabel(action.function)} — ${scoreLabel} — ${statusLabel}`}
          className={cn(
            "absolute flex size-7 -translate-x-1/2 translate-y-1/2 cursor-grab items-center justify-center rounded-full transition-[opacity,transform] duration-150 hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:cursor-grabbing motion-reduce:transition-none",
            DEPARTMENT_COLOR[action.function],
            highlighted && "z-10 scale-150 bg-card shadow-md",
            dimmed && "opacity-30"
          )}
          style={{ left: `${left}%`, bottom: `${bottom}%` }}
        >
          <span aria-hidden="true" className={cn(
            "size-3.5 rounded-full border-2 border-current ring-2 ring-card",
            action.status !== "rejected" && "bg-current",
            pending && "outline-2 outline-offset-2 outline-dashed outline-current/60"
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

// ------------------------------------------------------------------ Decision queue

/** Một dòng trong hàng chờ quyết định cạnh ma trận (mẫu Searchable "action
 * queue"): rê chuột vào dòng thì chấm tương ứng trên ma trận nổi lên. */
function QueueItem({
  action,
  highlighted,
  onHover,
  onOpen,
}: {
  action: ActionItem
  highlighted: boolean
  onHover: (id: string | null) => void
  onOpen: () => void
}) {
  const update = useUpdateAction()
  const eff = effectiveScores(action)
  const send = (status: "accepted" | "rejected") =>
    update.mutate(
      { actionId: action.id, body: { status } },
      {
        onSuccess: () =>
          toast.success(status === "accepted" ? "Đã nhận hành động." : "Đã từ chối hành động — vẫn giữ trong lịch sử."),
        onError: () => toast.error("Chưa lưu được quyết định. Thử lại sau giây lát."),
      }
    )
  return (
    <li
      onMouseEnter={() => onHover(action.id)}
      onMouseLeave={() => onHover(null)}
      onFocusCapture={() => onHover(action.id)}
      onBlurCapture={() => onHover(null)}
      className={cn(
        "flex flex-col gap-2 rounded-lg border bg-card p-3 transition-colors",
        highlighted && "border-ring/60 bg-accent/50"
      )}
    >
      <div className="flex items-center gap-2 text-xs">
        <span className={cn("flex items-center gap-1.5", DEPARTMENT_COLOR[action.function])}>
          <span aria-hidden="true" className="size-2 rounded-full bg-current" />
          <span className="text-muted-foreground">{departmentLabel(action.function)}</span>
        </span>
        <span className="ml-auto font-mono text-muted-foreground" title="Điểm ưu tiên">
          {action.priority_score.toFixed(1)}
        </span>
      </div>
      <button
        type="button"
        onClick={onOpen}
        className="line-clamp-3 rounded-sm text-left text-sm font-medium hover:underline focus-visible:outline-2 focus-visible:outline-ring"
      >
        {action.recommendation}
      </button>
      <p className="text-xs text-muted-foreground">
        {QUADRANT_VI[quadrantOf(eff.impact, eff.effort)]} · Tác động {eff.impact} · Nỗ lực {eff.effort}
      </p>
      <div className="flex flex-wrap gap-1.5">
        <Button size="xs" disabled={update.isPending} onClick={() => send("accepted")}>
          {update.isPending ? <Spinner data-icon="inline-start" /> : null}
          Nhận
        </Button>
        <Button size="xs" variant="outline" disabled={update.isPending} onClick={onOpen}>
          Chỉnh điểm
        </Button>
        <Button size="xs" variant="ghost" disabled={update.isPending} onClick={() => send("rejected")}>
          Từ chối
        </Button>
      </div>
    </li>
  )
}

/ ------------------------------------------------------------------ Add action dialog

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
          toast.success("Đã thêm và nhận hành động.")
          onOpenChange(false)
          setRecommendation("")
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Chưa thêm được hành động."
          ),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tự thêm hành động</DialogTitle>
          <DialogDescription>
            Chọn phòng ban, mô tả việc cần làm và chấm điểm. Hành động bạn tự
            thêm được tính là đã nhận.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="add-action-department">Phòng ban</FieldLabel>
            <Select
              value={fn}
              onValueChange={(v) => setFn(v as BusinessFunction)}
            >
              <SelectTrigger id="add-action-department">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {BUSINESS_FUNCTIONS.map((f) => (
                    <SelectItem key={f.value} value={f.value}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel htmlFor="add-action-text">Việc cần làm</FieldLabel>
            <Textarea
              id="add-action-text"
              rows={3}
              value={recommendation}
              onChange={(e) => setRecommendation(e.target.value)}
              placeholder="Ví dụ: Thêm nút thử lại khi tải ảnh thất bại"
            />
          </Field>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["Tác động", impact, setImpact],
                ["Nỗ lực", effort, setEffort],
                ["Khẩn cấp", urgency, setUrgency],
              ] as const
            ).map(([label, value, set]) => (
              <Field key={label}>
                <FieldLabel htmlFor={`add-action-${label}`}>{label} (1–10)</FieldLabel>
                <Input
                  id={`add-action-${label}`}
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
            Huỷ
          </Button>
          <Button
            disabled={recommendation.trim().length < 3 || add.isPending}
            onClick={submit}
          >
            {add.isPending ? <Spinner data-icon="inline-start" /> : null}
            Thêm và nhận hành động
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/// ------------------------------------------------------------------ Screen

const QUADRANT_LAYOUT = [
  ["quick_wins", "left-0 top-0", "text-leaf-ink", "left-3 top-3"],
  ["strategic_investments", "right-0 top-0", "text-sky-ink", "right-3 top-3"],
  ["low_priority", "left-0 bottom-0", "text-muted-foreground", "left-3 bottom-3"],
  ["reconsider", "right-0 bottom-0", "text-coral-ink", "right-3 bottom-3"],
] as const

function Matrix({ initialReportId }: { initialReportId: string | null }) {
  const lang = useAppLang()
  const t = useT()
  const insights = useInsights()
  const generate = useGenerateActions()
  const [generateError, setGenerateError] = useState(false)
  const [reportId, setReportId] = useState<string | null>(initialReportId)
  const [department, setDepartment] = useState("all")
  const [statusFilter, setStatusFilter] = useState("active")
  const [view, setView] = useState("matrix")
  const [openActionId, setOpenActionId] = useState<string | null>(null)
  const [hoverId, setHoverId] = useState<string | null>(null)
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

  // Derived selection: mặc định là kết luận ĐÃ DUYỆT mới nhất (chỉ nó tạo
  // được hành động), rồi mới tới kết luận đang chờ duyệt.
  const effectiveReportId =
    reportId ??
    [...eligibleReports]
      .filter((r) => r.status === "approved" || r.status === "edited")
      .sort((a, b) => b.created_at.localeCompare(a.created_at))[0]?.id ??
    eligibleReports[0]?.id ??
    null
  const selectedReport =
    eligibleReports.find((r) => r.id === effectiveReportId) ?? null
  const reportApproved =
    selectedReport?.status === "approved" || selectedReport?.status === "edited"

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

  // Tìm trong toàn bộ hành động: hàng chờ có thể mở việc đang bị bộ lọc ẩn.
  const openAction = allItems.find((a) => a.id === openActionId) ?? null
  const undecided = useMemo(
    () =>
      allItems
        .filter((a) => a.status === "proposed" || a.status === "edited")
        .sort((a, b) => b.priority_score - a.priority_score),
    [allItems]
  )
  const quadrantCount = useMemo(() => {
    const count: Record<Quadrant, number> = {
      quick_wins: 0,
      strategic_investments: 0,
      low_priority: 0,
      reconsider: 0,
    }
    for (const a of items) {
      const eff = effectiveScores(a)
      count[quadrantOf(eff.impact, eff.effort)] += 1
    }
    return count
  }, [items])

  const runGenerate = () => {
    if (!effectiveReportId) return
    setGenerateError(false)
    generate.mutate(effectiveReportId, {
      onSuccess: (result) => {
        setGenerateError(Boolean(result.generation_error))
        if (!result.generation_error && !result.actions_created)
          toast.info(t.matrixPage.noSuggestion)
      },
      onError: () => setGenerateError(true),
    })
  }

  const showBoard =
    !insights.isPending &&
    effectiveReportId &&
    reportApproved &&
    !actions.isError &&
    !actions.isPending &&
    allItems.length > 0

  return (
    <div className="flex flex-col gap-6">
      <NextStepBar />
      <PageHeader
        title={t.nav.items.matrix}
        description="Xếp hành động theo tác động và nỗ lực, rồi quyết định từng việc. Khuyến nghị gốc của AI luôn được giữ khi bạn chỉnh điểm."
        actions={
          <Button
            variant="outline"
            disabled={!effectiveReportId || !reportApproved}
            onClick={() => setAddOpen(true)}
          >
            <Plus data-icon="inline-start" />
            {t.matrixPage.addManual}
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select value={effectiveReportId ?? ""} onValueChange={setReportId}>
          <SelectTrigger className="w-full sm:w-80" aria-label="Kết luận nguồn">
            <SelectValue placeholder="Chọn kết luận" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {eligibleReports.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  Kết luận: {r.title}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <Select value={department} onValueChange={setDepartment}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Lọc theo phòng ban">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="all">Phòng ban: tất cả</SelectItem>
              {BUSINESS_FUNCTIONS.map((f) => (
                <SelectItem key={f.value} value={f.label.toLowerCase()}>
                  Phòng ban: {f.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Lọc theo trạng thái">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="active">Trạng thái: đang mở</SelectItem>
              <SelectItem value="accepted">Trạng thái: đã nhận</SelectItem>
              <SelectItem value="rejected">Trạng thái: đã từ chối</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
        {showBoard ? (
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            spacing={0}
            value={view}
            onValueChange={(v) => v && setView(v)}
            aria-label={lang === "vi" ? "Chế độ xem ưu tiên" : "Priority view"}
            className="sm:ml-auto"
          >
            <ToggleGroupItem value="matrix" aria-label="Xem dạng ma trận">
              <LayoutGrid />
              {lang === "vi" ? "Ma trận" : "Matrix"}
            </ToggleGroupItem>
            <ToggleGroupItem value="table" aria-label="Xem dạng bảng">
              <Rows3 />
              {lang === "vi" ? "Bảng" : "Table"}
            </ToggleGroupItem>
          </ToggleGroup>
        ) : null}
      </div>

      {insights.isPending ? (
        <Spinner />
      ) : !effectiveReportId ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>{t.matrixPage.noReportTitle}</EmptyTitle>
            <EmptyDescription>{t.matrixPage.noReportBody}</EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link href="/data-graph?ask=1">{t.matrixPage.noReportCta}</Link>
          </Button>
        </Empty>
      ) : !reportApproved ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>{t.matrixPage.notApprovedTitle}</EmptyTitle>
            <EmptyDescription>{t.matrixPage.notApprovedBody}</EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link
              href={
                selectedReport?.run_id
                  ? `/data-graph?run=${selectedReport.run_id}`
                  : `/reports?report=${effectiveReportId}`
              }
            >
              {t.matrixPage.reviewIt}
            </Link>
          </Button>
        </Empty>
      ) : actions.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Chưa tải được hành động</AlertTitle>
          <AlertDescription>
            {actions.error.message} — hành động vẫn được giữ trên máy chủ.
          </AlertDescription>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 w-fit"
            onClick={() => void actions.refetch()}
          >
            Tải lại
          </Button>
        </Alert>
      ) : actions.isPending ? (
        <Spinner />
      ) : allItems.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>{t.matrixPage.noActionsTitle}</EmptyTitle>
            <EmptyDescription>{t.matrixPage.noActionsBody}</EmptyDescription>
          </EmptyHeader>
          <Button
            size="lg"
            disabled={generate.isPending}
            onClick={runGenerate}
          >
            {generate.isPending ? <Spinner data-icon="inline-start" /> : null}
            {generate.isPending
              ? t.matrixPage.generating
              : t.matrixPage.generate}
          </Button>
          {generateError ? (
            <p role="alert" className="text-sm text-destructive">
              {t.matrixPage.generateFailed}
            </p>
          ) : null}
        </Empty>
      ) : (
        <div
          className={cn(
            "grid min-w-0 items-start gap-6",
            undecided.length > 0 && "xl:grid-cols-[minmax(0,1fr)_minmax(18rem,22rem)]"
          )}
        >
          <Card className="min-w-0">
            <CardHeader>
              <CardTitle>{lang === "vi" ? "Ưu tiên hành động" : "Action priorities"}</CardTitle>
              <CardDescription>
                {view === "matrix"
                  ? lang === "vi"
                    ? "Mỗi chấm là một hành động, màu theo phòng ban; viền nét đứt là việc chờ bạn quyết định. Bấm để mở chi tiết hoặc kéo thả để chỉnh ưu tiên."
                    : "Each dot is an action, colored by department; a dashed ring means it awaits your decision. Click for details or drag to adjust."
                  : lang === "vi"
                    ? "Sắp theo điểm ưu tiên. Chọn hành động để xem chi tiết và chỉnh điểm."
                    : "Sorted by priority. Select an action to review details and scores."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex min-w-0 flex-col gap-4">
              {items.length === 0 ? (
                <Empty className="border">
                  <EmptyHeader>
                    <EmptyTitle>{t.matrixPage.filteredEmpty}</EmptyTitle>
                  </EmptyHeader>
                </Empty>
              ) : view === "matrix" ? (
                <>
                  <div className="flex items-stretch gap-2">
                    <span
                      aria-hidden="true"
                      className="flex shrink-0 items-center text-xs text-muted-foreground [writing-mode:vertical-rl] rotate-180"
                    >
                      Tác động tới khách hàng →
                    </span>
                    <div
                      className="relative h-[clamp(20rem,55vh,30rem)] min-w-0 flex-1 overflow-hidden rounded-lg border bg-card"
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
                      {QUADRANT_LAYOUT.map(([quadrant, area, ink, pos]) => (
                        <div key={quadrant} className={cn("absolute h-1/2 w-1/2", area, QUADRANT_TINT[quadrant])}>
                          <span
                            className={cn(
                              "absolute flex items-baseline gap-1.5 text-xs font-semibold tracking-wide uppercase",
                              pos,
                              ink,
                            )}
                          >
                            {QUADRANT_VI[quadrant]}
                            <span className="font-mono font-normal normal-case opacity-70">
                              {quadrantCount[quadrant]}
                            </span>
                          </span>
                        </div>
                      ))}
                      <div className="absolute top-0 left-1/2 h-full w-px bg-border" />
                      <div className="absolute top-1/2 left-0 h-px w-full bg-border" />
                      {items.map((a) => (
                        <MatrixPoint
                          key={a.id}
                          action={a}
                          highlighted={hoverId === a.id}
                          dimmed={hoverId != null && hoverId !== a.id}
                          onHover={setHoverId}
                          onOpen={() => setOpenActionId(a.id)}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-between pl-6 text-xs text-muted-foreground">
                    <span>Nỗ lực thấp</span>
                    <span>Nỗ lực cao →</span>
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
                </>
              ) : (
                <div className="min-w-0 overflow-x-auto rounded-lg border">
                  <Table className="min-w-[38rem]">
                    <TableHeader className="bg-muted/50">
                      <TableRow>
                        <TableHead>{lang === "vi" ? "Hành động" : "Action"}</TableHead>
                        <TableHead>{lang === "vi" ? "Nhóm ưu tiên" : "Quadrant"}</TableHead>
                        <TableHead>{lang === "vi" ? "Trạng thái" : "Status"}</TableHead>
                        <TableHead className="text-right">{lang === "vi" ? "Tác động" : "Impact"}</TableHead>
                        <TableHead className="text-right">{lang === "vi" ? "Nỗ lực" : "Effort"}</TableHead>
                        <TableHead className="text-right">{lang === "vi" ? "Ưu tiên" : "Priority"}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...items]
                        .sort((a, b) => b.priority_score - a.priority_score)
                        .map((action) => {
                          const scores = effectiveScores(action)
                          return (
                            <TableRow
                              key={action.id}
                              data-state={hoverId === action.id ? "selected" : undefined}
                              onMouseEnter={() => setHoverId(action.id)}
                              onMouseLeave={() => setHoverId(null)}
                            >
                              <TableCell className="max-w-sm whitespace-normal wrap-anywhere">
                                <button
                                  type="button"
                                  className="rounded-sm text-left font-medium hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                                  onClick={() => setOpenActionId(action.id)}
                                >
                                  {action.recommendation}
                                </button>
                                <span className={cn("mt-0.5 flex items-center gap-1.5 text-xs", DEPARTMENT_COLOR[action.function])}>
                                  <span aria-hidden="true" className="size-2 rounded-full bg-current" />
                                  <span className="text-muted-foreground">{departmentLabel(action.function)}</span>
                                </span>
                              </TableCell>
                              <TableCell className="text-sm">{QUADRANT_VI[quadrantOf(scores.impact, scores.effort)]}</TableCell>
                              <TableCell>{lang === "vi" ? ACTION_STATUS_VI[action.status] ?? action.status : action.status}</TableCell>
                              <TableCell className="text-right tabular-nums">{scores.impact}</TableCell>
                              <TableCell className="text-right tabular-nums">{scores.effort}</TableCell>
                              <TableCell className="text-right font-medium tabular-nums">{action.priority_score.toFixed(1)}</TableCell>
                            </TableRow>
                          )
                        })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex-wrap justify-between gap-2">
              <span className="text-xs text-muted-foreground">
                {lang === "vi"
                  ? "Điểm ưu tiên còn tính cả độ khẩn cấp và độ tin cậy."
                  : "Priority also accounts for urgency and confidence."}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/reports?report=${effectiveReportId}`}>
                    {t.matrixPage.sourceReport}
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/stakeholders?report=${effectiveReportId}`}>
                    {t.matrixPage.byDepartment}
                  </Link>
                </Button>
              </div>
            </CardFooter>
          </Card>

          {undecided.length > 0 ? (
            <Card size="sm" id="pending-action-review" className="scroll-mt-24 xl:sticky xl:top-20">
              <CardHeader>
                <CardTitle>{t.matrixPage.decideTitle(undecided.length)}</CardTitle>
                <CardDescription>{t.matrixPage.decideBody}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="-mx-1 flex max-h-[min(70vh,40rem)] flex-col gap-2 overflow-y-auto px-1 pb-1">
                  {undecided.map((action) => (
                    <QueueItem
                      key={action.id}
                      action={action}
                      highlighted={hoverId === action.id}
                      onHover={setHoverId}
                      onOpen={() => setOpenActionId(action.id)}
                    />
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
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

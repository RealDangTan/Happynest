"use client"
import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import {
  getCoreRowModel,
  getSortedRowModel,
  useLegacyTable,
  type LegacyColumnDef,
} from "@tanstack/react-table/legacy"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import {
  DataTable,
  DataTableColumnHeader,
  DataTableToolbar,
} from "@/components/data-table"
import { AiBadge } from "@/components/ai/ai-badge"
import { PageHeader } from "@/components/page-header"
import { NextStepBar } from "@/components/journey/next-step-bar"
import { ACTION_STATUS_TONE } from "@/lib/tone"
import { useT } from "@/lib/i18n"
import { useInsights } from "@/hooks/use-insights"
import { useActions } from "@/hooks/use-actions"
import { ActionDecisionSupport } from "@/components/actions/action-decision-support"
import { DEPARTMENTS, departmentLabel, toDepartment } from "@/lib/departments"
import {
  countByStatus,
  filterStakeholderActions,
  type StakeholderStatusFilter,
} from "@/lib/stakeholders"
import { cn } from "@/lib/utils"
import { effectiveScores } from "@/lib/matrix"
import type { ActionItem } from "@/lib/types"

// Cùng màu chấm phòng ban với Ma trận ưu tiên — nhận ra nhóm bằng màu.
const DEPARTMENT_DOT: Record<string, string> = {
  engineering: "text-department-engineering",
  support: "text-department-support",
  design: "text-department-design",
  marketing: "text-department-marketing",
  legal: "text-department-legal",
  finance: "text-department-finance",
  operations: "text-department-operations",
  sales: "text-department-sales",
}

const STATUS_LABEL: Record<string, string> = {
  accepted: "Đã nhận",
  proposed: "Đề xuất",
  edited: "Đã chỉnh",
  rejected: "Từ chối",
}

function ActionsTable({
  items,
  selectedId,
  onSelect,
}: {
  items: ActionItem[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const columns = useMemo<LegacyColumnDef<ActionItem>[]>(
    () => [
      {
        id: "recommendation",
        enableSorting: false,
        enableHiding: false,
        meta: { thClassName: "w-[58%]" },
        header: "Hành động",
        cell: ({ row }) => (
          <>
            <span className="flex items-start gap-2">
              {selectedId === row.original.id ? (
                <span aria-hidden className="mt-0.5">
                  ›
                </span>
              ) : (
                <span className="w-2" aria-hidden />
              )}
              <span className="min-w-0 text-sm break-words">
                {row.original.recommendation}
              </span>
            </span>
            <span className="mt-1 block pl-4 font-mono text-xs text-muted-foreground">
              {departmentLabel(row.original.function)}
            </span>
          </>
        ),
      },
      {
        id: "priority",
        accessorFn: (a: ActionItem) => a.priority_score,
        sortDescFirst: true,
        meta: { label: "Ưu tiên", thClassName: "w-24", tdClassName: "w-24" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Ưu tiên" />
        ),
        cell: ({ row }) => {
          const score = row.original.priority_score
          const [label, tone] =
            score >= 7
              ? (["Cao", "danger"] as const)
              : score >= 4
                ? (["Vừa", "warning"] as const)
                : (["Thấp", "info"] as const)
          return <Badge variant={tone}>{label}</Badge>
        },
      },
      {
        id: "status",
        accessorFn: (a: ActionItem) => a.status,
        meta: { label: "Trạng thái", thClassName: "w-28", tdClassName: "w-28" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Trạng thái" />
        ),
        cell: ({ row }) => (
          <Badge variant={ACTION_STATUS_TONE[row.original.status] ?? "secondary"}>
            {STATUS_LABEL[row.original.status] ?? row.original.status}
          </Badge>
        ),
      },
    ],
    [selectedId],
  )

  const table = useLegacyTable({
    data: items,
    columns,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    globalFilterFn: "includesString",
    initialState: { sorting: [{ id: "priority", desc: true }] },
  })

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <DataTableToolbar table={table} hideColumnToggle />
      <Card className="py-0">
        <CardContent className="p-0">
          <DataTable
            table={table}
            onRowClick={(row) => onSelect(row.id)}
            rowClassName={(row) => (row.id === selectedId ? "bg-accent" : undefined)}
          />
        </CardContent>
      </Card>
    </div>
  )
}

function Stakeholders({ initialReportId }: { initialReportId: string | null }) {
  const t = useT()
  const insights = useInsights()
  const [reportId, setReportId] = useState<string | null>(initialReportId)
  const [statusFilter, setStatusFilter] =
    useState<StakeholderStatusFilter>("accepted")
  const [department, setDepartment] = useState("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const eligibleReports = useMemo(
    () => (insights.data?.items ?? []).filter((i) => i.status !== "pending"),
    [insights.data]
  )

  // Derived selection: falls back to the first eligible report.
  const effectiveReportId = reportId ?? eligibleReports[0]?.id ?? null

  const actions = useActions(effectiveReportId)
  const allItems = useMemo(() => actions.data?.items ?? [], [actions.data])

  const filtered = useMemo(
    () =>
      filterStakeholderActions(allItems, {
        department,
        status: statusFilter,
        selectedId,
      }),
    [allItems, department, statusFilter, selectedId]
  )
  const statusCounts = useMemo(() => countByStatus(allItems), [allItems])

  const selected = allItems.find((a) => a.id === selectedId) ?? null

  const departmentCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const a of allItems) {
      const key = toDepartment(a.function)
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return counts
  }, [allItems])

  // Empty state phải nói đúng lý do: kết luận chưa có hành động nào, hay có
  // nhưng đang bị bộ lọc trạng thái/phòng ban ẩn đi (HN-010).
  const hiddenByStatus =
    statusFilter === "all"
      ? 0
      : filterStakeholderActions(allItems, {
          department,
          status: "all",
          selectedId,
        }).length
  const statusName: Record<StakeholderStatusFilter, string> = {
    all: "tất cả",
    accepted: "đã nhận",
    proposed: "đề xuất",
    edited: "đã chỉnh",
    rejected: "đã từ chối",
  }

  return (
    <div className="flex flex-col gap-6">
      <NextStepBar />
      <PageHeader
        title={t.nav.items.stakeholders}
        description="Gói insight thành bản tin cho từng phòng ban — ai cần biết gì, vì sao."
      />

      <Card size="sm">
        <CardContent className="flex-row flex-wrap items-center gap-2">
          <Select value={effectiveReportId ?? ""} onValueChange={setReportId}>
            <SelectTrigger className="w-72">
              <SelectValue placeholder="Chọn kết luận" />
            </SelectTrigger>
            <SelectContent>
              {eligibleReports.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  Kết luận: {r.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={statusFilter}
            onValueChange={(value) =>
              setStatusFilter(value as StakeholderStatusFilter)
            }
          >
            <SelectTrigger className="w-60" aria-label="Lọc theo trạng thái">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                Trạng thái: tất cả ({allItems.length})
              </SelectItem>
              <SelectItem value="accepted">
                Trạng thái: đã nhận ({statusCounts.accepted ?? 0})
              </SelectItem>
              <SelectItem value="proposed">
                Trạng thái: đề xuất ({statusCounts.proposed ?? 0})
              </SelectItem>
              <SelectItem value="edited">
                Trạng thái: đã chỉnh ({statusCounts.edited ?? 0})
              </SelectItem>
              <SelectItem value="rejected">
                Trạng thái: đã từ chối ({statusCounts.rejected ?? 0})
              </SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <div className="grid min-w-0 gap-6 lg:grid-cols-[200px_minmax(0,1fr)_minmax(300px,380px)]">
        {/* By department */}
        <aside className="flex flex-col gap-1">
          <h2 className="px-2 pb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Theo phòng ban
          </h2>
          {["all", ...DEPARTMENTS.map((d) => d.toLowerCase())].map((key) => (
            <button
              key={key}
              onClick={() => setDepartment(key)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
                department === key ? "bg-accent font-medium" : "hover:bg-accent/60"
              )}
            >
              {department === key ? (
                <span aria-hidden>›</span>
              ) : (
                <span className="w-2" aria-hidden />
              )}
              {key !== "all" ? (
                <span
                  aria-hidden
                  className={`size-2 shrink-0 rounded-full bg-current ${DEPARTMENT_DOT[key] ?? ""}`}
                />
              ) : null}
              <span className={`flex-1 ${key === "all" ? "" : "capitalize"}`}>
                {key === "all" ? "Tất cả" : key}
              </span>
              {key !== "all" && (departmentCounts.get(key) ?? 0) > 0 ? (
                <span className="font-mono text-xs text-muted-foreground">
                  {departmentCounts.get(key)}
                </span>
              ) : null}
            </button>
          ))}
        </aside>

        {/* Actions table */}
        {actions.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Không tải được actions</AlertTitle>
            <AlertDescription className="flex flex-col gap-3">
              <span>{actions.error.message}</span>
              <div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void actions.refetch()}
                >
                  Thử lại
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        ) : actions.isPending ? (
          <Spinner />
        ) : filtered.length === 0 ? (
          <Empty className="border">
            <EmptyHeader>
              <EmptyTitle>
                {allItems.length === 0
                  ? "Kết luận này chưa có hành động"
                  : hiddenByStatus > 0
                    ? `Không có hành động ở trạng thái “${statusName[statusFilter]}”`
                    : "Phòng ban này chưa có hành động"}
              </EmptyTitle>
              <EmptyDescription>
                {allItems.length === 0
                  ? "Hành động chỉ xuất hiện sau khi bạn tạo gợi ý và nhận việc từ kết luận đã duyệt."
                  : hiddenByStatus > 0
                    ? `Có ${hiddenByStatus} hành động ở trạng thái khác đang bị bộ lọc ẩn đi.`
                    : "Chọn “Tất cả” ở cột phòng ban để xem hành động của các nhóm khác."}
              </EmptyDescription>
            </EmptyHeader>
            <div className="flex flex-wrap justify-center gap-2">
              {allItems.length > 0 && hiddenByStatus > 0 ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setStatusFilter("all")}
                >
                  Xem tất cả trạng thái ({hiddenByStatus})
                </Button>
              ) : null}
              {allItems.length > 0 && hiddenByStatus === 0 ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setDepartment("all")}
                >
                  Xem mọi phòng ban
                </Button>
              ) : null}
              <Button size="sm" variant="outline" asChild>
                <Link href={`/matrix?report=${effectiveReportId ?? ""}`}>
                  {allItems.length === 0
                    ? "Tạo hành động ở Ma trận ưu tiên"
                    : "Mở Ma trận ưu tiên"}
                </Link>
              </Button>
            </div>
          </Empty>
        ) : (
          <ActionsTable
            items={filtered}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}

        {/* WHAT panel */}
        <Card size="sm" className="self-start">
          <CardHeader>
            <CardTitle>Việc cần làm</CardTitle>
            <CardDescription>
              Mỗi phòng ban cần làm gì dựa trên action được chọn.
            </CardDescription>
          </CardHeader>
          {selected ? (
            <CardContent className="flex flex-col gap-4">
              <div>
                <p className="font-heading text-base leading-snug">
                  {selected.recommendation}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="outline">
                    {departmentLabel(selected.function)}
                  </Badge>
                  <AiBadge />
                </div>
              </div>
              {selected.rationale ? (
                <div className="flex flex-col gap-1 text-sm">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                    Lý do đề xuất
                  </h3>
                  <p>{selected.rationale}</p>
                </div>
              ) : null}
              <div className="flex flex-col gap-1 text-sm">
                <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  Căn cứ
                </h3>
                <p>
                  Từ kết luận trong{" "}
                  <Link
                    className="text-signal underline"
                    href={`/reports?report=${selected.insight_id}`}
                  >
                    báo cáo
                  </Link>{" "}
                  · Tác động {effectiveScores(selected).impact}/10 · Nỗ lực{" "}
                  {effectiveScores(selected).effort}/10
                </p>
              </div>
              <ActionDecisionSupport action={selected} />
              <div className="flex flex-col gap-2">
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/reports?report=${selected.insight_id}`}>
                    Mở báo cáo
                  </Link>
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/matrix?report=${selected.insight_id}`}>
                    Xem trên ma trận
                  </Link>
                </Button>
              </div>
            </CardContent>
          ) : (
            <CardContent className="text-sm text-muted-foreground">
              Chọn một hành động để xem từng phòng ban cần làm gì và bằng
              chứng đằng sau quyết định.
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}

export default function StakeholdersPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <StakeholdersWithParams />
    </Suspense>
  )
}

function StakeholdersWithParams() {
  const params = useSearchParams()
  return <Stakeholders initialReportId={params.get("report")} />
}

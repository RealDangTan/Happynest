"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import { Suspense, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import type {
  ColumnFiltersState,
  ColumnVisibilityState,
} from "@tanstack/react-table"
import {
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  useLegacyTable,
  type LegacyColumnDef,
} from "@tanstack/react-table/legacy"
import { useFeedbacks } from "@/hooks/use-feedbacks"
import { useProduct } from "@/hooks/use-product"
import { useTaxonomy } from "@/hooks/use-taxonomy"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { useStoredState } from "@/hooks/use-stored-state"
import type { Feedback } from "@/lib/types"
import { formatDate } from "@/lib/format"
import { topicLabeler } from "@/lib/graph"
import {
  multiSelectFilterFn,
  serverSortToSorting,
  sortingToServerSort,
} from "@/lib/table-sorts"
import { SENTIMENT_LABEL, SEVERITY_LABEL } from "@/lib/labels"
import { useAppLang } from "@/lib/i18n"
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  DataTableToolbar,
} from "@/components/data-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { DataEntryDialog } from "./data-entry-dialog"
import { PageHeader } from "@/components/page-header"

/** Cột bật/tắt được; "content" luôn hiển thị (enableHiding: false). */
const DEFAULT_VISIBILITY: ColumnVisibilityState = {
  source: true,
  occurred_at: true,
  severity: true,
  sentiment: false,
  topics: true,
  confidence: false,
  pii: false,
}
const STORAGE_KEY = "feedbacks.columns.v2"

function FeedbacksTable() {
  const router = useRouter()
  const sp = useSearchParams()
  const lang = useAppLang()
  const page = Math.max(1, Number(sp.get("page") ?? "1") || 1)
  const pageSize = Math.min(100, Math.max(10, Number(sp.get("limit") ?? "20") || 20))
  const q = sp.get("q") ?? ""
  const topic = sp.get("topic") ?? ""

  // ── URL-param state ────────────────────────────────────────────────
  const sorting = useMemo(() => serverSortToSorting(sp.get("sort") ?? undefined), [sp])

  const columnFilters = useMemo<ColumnFiltersState>(() => {
    const out: ColumnFiltersState = []
    const sev = sp.get("severity")
    const sen = sp.get("sentiment")
    if (sev) out.push({ id: "severity", value: sev.split(",") })
    if (sen) out.push({ id: "sentiment", value: sen.split(",") })
    return out
  }, [sp])

  const pagination = { pageIndex: page - 1, pageSize }

  const [columnVisibility, setColumnVisibility] = useStoredState<ColumnVisibilityState>(
    STORAGE_KEY,
    DEFAULT_VISIBILITY,
    (raw) => {
      try {
        const parsed = JSON.parse(raw) as ColumnVisibilityState
        return parsed && typeof parsed === "object" ? parsed : null
      } catch {
        return null
      }
    },
  )

  function navigate(next: URLSearchParams) {
    router.replace(`/feedbacks?${next.toString()}`)
  }

  /** Set/DEL một param; đổi filter (khác page) → về trang 1. */
  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(sp.toString())
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== "page") next.delete("page")
    navigate(next)
  }

  // Search debounce 300ms — không query server từng keystroke.
  const [searchInput, setSearchInput] = useState(q)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- đồng bộ input khi URL param đổi từ ngoài (reset filters)
    setSearchInput(q)
  }, [q])
  const debouncedSearch = useDebouncedValue(searchInput, 300)
  useEffect(() => {
    if (debouncedSearch !== q) setParam("q", debouncedSearch.trim() || null)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- chủ đích: chỉ chạy khi giá trị debounce đổi
  }, [debouncedSearch])

  // ── Data ───────────────────────────────────────────────────────────
  const { data, isFetching, isError, error } = useFeedbacks({
    page,
    pageSize,
    q: q || undefined,
    sort: sortingToServerSort(sorting),
    severity: (columnFilters.find((f) => f.id === "severity")?.value as string[]) ?? undefined,
    sentiment: (columnFilters.find((f) => f.id === "sentiment")?.value as string[]) ?? undefined,
    topic: topic || undefined,
  })

  const { productId } = useProduct()
  const taxonomy = useTaxonomy(productId)
  const labelTopic = useMemo(
    () => topicLabeler(taxonomy.data?.items ?? []),
    [taxonomy.data],
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

  // ── Columns ────────────────────────────────────────────────────────
  const columns = useMemo<LegacyColumnDef<Feedback>[]>(
    () => [
      {
        id: "content",
        enableHiding: false,
        enableSorting: false,
        meta: { label: "Nội dung", thClassName: "w-[42%]" },
        header: "Nội dung",
        cell: ({ row }) => (
          <Link href={`/feedbacks/${row.original.id}`} className="block max-w-md">
            <span className="line-clamp-2 break-words">
              {row.original.feedback_text ?? "(chưa phân tích)"}
            </span>
          </Link>
        ),
      },
      {
        id: "source",
        accessorFn: (f: Feedback) => f.source,
        meta: { label: "Nguồn" },
        header: ({ column }) => <DataTableColumnHeader column={column} title="Nguồn" />,
        cell: ({ row }) => row.original.source,
      },
      {
        id: "occurred_at",
        accessorFn: (f: Feedback) => f.occurred_at,
        meta: { label: "Thời điểm" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Thời điểm" />
        ),
        cell: ({ row }) => (
          <span className="whitespace-nowrap">{formatDate(row.original.occurred_at)}</span>
        ),
      },
      {
        id: "severity",
        accessorFn: (f: Feedback) => f.ai_analysis?.severity ?? "",
        filterFn: multiSelectFilterFn,
        sortDescFirst: true,
        meta: { label: "Mức độ" },
        header: ({ column }) => <DataTableColumnHeader column={column} title="Mức độ" />,
        cell: ({ row }) => {
          const severity = row.original.ai_analysis?.severity
          return severity ? (
            <Badge
              variant={severity === "critical" || severity === "high" ? "destructive" : "secondary"}
            >
              {SEVERITY_LABEL[lang][severity]}
            </Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
      {
        id: "sentiment",
        accessorFn: (f: Feedback) => f.ai_analysis?.sentiment ?? "",
        enableSorting: false,
        filterFn: multiSelectFilterFn,
        meta: { label: "Cảm xúc" },
        header: ({ column }) => <DataTableColumnHeader column={column} title="Cảm xúc" />,
        cell: ({ row }) => {
          const sentiment = row.original.ai_analysis?.sentiment
          return sentiment ? (
            <SentimentIndicator value={sentiment} />
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
      {
        id: "topics",
        enableSorting: false,
        meta: { label: "Chủ đề", tdClassName: "max-w-48" },
        header: ({ column }) => <DataTableColumnHeader column={column} title="Chủ đề" />,
        cell: ({ row }) => {
          const topics = row.original.ai_analysis?.topics
          return topics?.length ? (
            <div className="flex flex-wrap gap-1">
              {topics.slice(0, 3).map((t) => (
                <Badge key={t} variant="outline" title={t}>
                  {labelTopic(t)}
                </Badge>
              ))}
            </div>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
      {
        id: "confidence",
        accessorFn: (f: Feedback) => f.ai_analysis?.confidence ?? -1,
        sortDescFirst: true,
        meta: { label: "Confidence", thClassName: "text-right", tdClassName: "text-right" },
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Confidence" className="justify-end" />
        ),
        cell: ({ row }) => {
          const confidence = row.original.ai_analysis?.confidence
          return confidence != null ? (
            <span className="tabular-nums">{`${Math.round(confidence * 100)}%`}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
      {
        id: "pii",
        enableSorting: false,
        meta: { label: "PII" },
        header: ({ column }) => <DataTableColumnHeader column={column} title="PII" />,
        cell: ({ row }) =>
          row.original.pii_detected ? (
            <Badge variant="outline">PII</Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
    ],
    [lang, labelTopic],
  )

  const total = data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / pageSize))

  const table = useLegacyTable({
    data: data?.items ?? [],
    columns,
    manualPagination: true,
    pageCount,
    manualSorting: true,
    manualFiltering: true,
    enableMultiSort: false,
    getCoreRowModel: getCoreRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    state: { sorting, columnFilters, columnVisibility, pagination },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater
      setParam("sort", next.length ? sortingToServerSort(next) : null)
    },
    onColumnFiltersChange: (updater) => {
      const next = typeof updater === "function" ? updater(columnFilters) : updater
      const params = new URLSearchParams(sp.toString())
      const sev = next.find((f) => f.id === "severity")?.value as string[] | undefined
      const sen = next.find((f) => f.id === "sentiment")?.value as string[] | undefined
      if (sev?.length) params.set("severity", sev.join(","))
      else params.delete("severity")
      if (sen?.length) params.set("sentiment", sen.join(","))
      else params.delete("sentiment")
      params.delete("page")
      navigate(params)
    },
    onColumnVisibilityChange: (updater) => {
      setColumnVisibility(
        typeof updater === "function" ? updater(columnVisibility) : updater,
      )
    },
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater(pagination) : updater
      const params = new URLSearchParams(sp.toString())
      if (next.pageSize !== pageSize) {
        params.set("limit", String(next.pageSize))
        params.delete("page")
      } else if (next.pageIndex !== page - 1) {
        params.set("page", String(next.pageIndex + 1))
      }
      navigate(params)
    },
  })

  const hasActiveFilters =
    columnFilters.length > 0 || q.trim() !== "" || topic !== ""

  if (isError)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Không tải được dữ liệu</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )

  return (
    <div className="flex flex-col gap-4">
      <DataTableToolbar
        table={table}
        search={{ value: searchInput, onChange: setSearchInput }}
        filters={[
          {
            columnId: "severity",
            title: "Mức độ",
            options: Object.entries(SEVERITY_LABEL[lang]).map(([value, label]) => ({
              value,
              label,
            })),
          },
          {
            columnId: "sentiment",
            title: "Cảm xúc",
            options: Object.entries(SENTIMENT_LABEL[lang]).map(([value, label]) => ({
              value,
              label,
            })),
          },
        ]}
      >
        <Select
          value={topic || "all"}
          onValueChange={(v) => setParam("topic", v === "all" ? null : v)}
        >
          <SelectTrigger size="sm" className="w-40">
            <SelectValue placeholder="Chủ đề" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Mọi chủ đề</SelectItem>
            {topicOptions.map((n) => (
              <SelectItem key={n.id} value={n.slug ?? n.name}>
                {n.name_vi ?? n.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </DataTableToolbar>

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          <DataTable
            table={table}
            isLoading={isFetching && !data}
            emptyContent={
              total === 0 && !hasActiveFilters ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>Chưa có phản hồi nào</EmptyTitle>
                    <EmptyDescription>
                      Nhập dữ liệu bằng nút bên trên (thủ công hoặc import CSV qua
                      LISTEN).
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>Không có phản hồi nào khớp</EmptyTitle>
                    <EmptyDescription>
                      Thử bỏ bớt từ khoá tìm kiếm hoặc bộ lọc.
                    </EmptyDescription>
                  </EmptyHeader>
                  {hasActiveFilters ? (
                    <EmptyContent>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(new URLSearchParams())}
                      >
                        Xoá mọi bộ lọc
                      </Button>
                    </EmptyContent>
                  ) : null}
                </Empty>
              )
            }
          />
        </CardContent>
        <CardContent className="border-t py-3">
          <DataTablePagination
            table={table}
            pageSizeOptions={[10, 20, 50, 100]}
          />
        </CardContent>
      </Card>
    </div>
  )
}

export default function FeedbacksPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Phản hồi"
        description="Mọi phản hồi đã nhập — tìm, lọc, sắp xếp và mở chi tiết từng mục."
        actions={<DataEntryDialog />}
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <FeedbacksTable />
      </Suspense>
    </div>
  )
}

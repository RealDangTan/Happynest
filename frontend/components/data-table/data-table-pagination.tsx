"use client"

import type { LegacyReactTable } from "@tanstack/react-table/legacy"
import type { RowData } from "@tanstack/react-table"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import { useT } from "@/lib/i18n"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/** Trang số hiển thị: tối đa 5 số + "…" hai đầu (pattern pagination quen mắt). */
function pageList(page: number, totalPages: number): (number | "…")[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
  const out = new Set<number>([1, totalPages, page - 1, page, page + 1])
  const sorted = [...out].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b)
  const result: (number | "…")[] = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) result.push("…")
    result.push(p)
    prev = p
  }
  return result
}

/**
 * Footer phân trang gọn: "a–b trên n" + chọn số dòng/trang + nút trang
 * đầu/trước/số/trước/cuối (icon). Hoạt động cả client (getPaginationRowModel)
 * lẫn server (manualPagination + pageCount).
 */
export function DataTablePagination<TData extends RowData>({
  table,
  pageSizeOptions = [10, 20, 50, 100],
}: {
  table: LegacyReactTable<TData>
  pageSizeOptions?: number[]
}) {
  const t = useT()
  const { pageIndex, pageSize } = table.state.pagination
  const totalRows = table.getRowCount()
  const totalPages = Math.max(1, table.getPageCount())
  const from = totalRows === 0 ? 0 : pageIndex * pageSize + 1
  const to = Math.min((pageIndex + 1) * pageSize, totalRows)

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-sm text-muted-foreground">
      <div className="flex items-center gap-3">
        <span className="tabular-nums">{t.table.rangeOf(from, to, totalRows)}</span>
        <span className="flex items-center gap-1.5">
          <span className="sr-only">{t.table.rowsPerPage}</span>
          <Select
            value={String(pageSize)}
            onValueChange={(v) => table.setPageSize(Number(v))}
          >
            <SelectTrigger
              size="sm"
              className="w-16 font-mono text-xs tabular-nums"
              aria-label={t.table.rowsPerPage}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </span>
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          disabled={!table.getCanPreviousPage()}
          onClick={() => table.setPageIndex(0)}
          aria-label={t.table.goToFirstPage}
        >
          <ChevronsLeft />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          disabled={!table.getCanPreviousPage()}
          onClick={() => table.previousPage()}
          aria-label={t.table.goToPreviousPage}
        >
          <ChevronLeft />
        </Button>
        {pageList(pageIndex + 1, totalPages).map((p, i) =>
          p === "…" ? (
            <span key={`ellipsis-${i}`} className="px-1 select-none">
              …
            </span>
          ) : (
            <Button
              key={p}
              variant={p === pageIndex + 1 ? "default" : "outline"}
              size="icon-sm"
              className="font-mono text-xs tabular-nums"
              onClick={() => table.setPageIndex(p - 1)}
              aria-label={t.table.pageOf(p, totalPages)}
              aria-current={p === pageIndex + 1 ? "page" : undefined}
            >
              {p}
            </Button>
          ),
        )}
        <Button
          variant="outline"
          size="icon-sm"
          disabled={!table.getCanNextPage()}
          onClick={() => table.nextPage()}
          aria-label={t.table.goToNextPage}
        >
          <ChevronRight />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          disabled={!table.getCanNextPage()}
          onClick={() => table.setPageIndex(totalPages - 1)}
          aria-label={t.table.goToLastPage}
        >
          <ChevronsRight />
        </Button>
      </div>
    </div>
  )
}

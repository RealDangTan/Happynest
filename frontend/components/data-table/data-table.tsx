"use client"

import { useState, type ReactNode } from "react"
import { flexRender } from "@tanstack/react-table"
import type { RowData } from "@tanstack/react-table"
import type { LegacyReactTable } from "@tanstack/react-table/legacy"
import { useT } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import "./types"

type DataTableProps<TData extends RowData> = {
  table: LegacyReactTable<TData>
  /** Đang tải trang dữ liệu mới → render skeleton thay rows */
  isLoading?: boolean
  /** Nội dung thay khi 0 dòng sau lọc (mặc định: Empty "không khớp") */
  emptyContent?: ReactNode
  /** Có scroll dọc trong khung + sticky header, ví dụ "max-h-[65vh]" */
  maxHeightClass?: string
  /** Bấm cả dòng (FE pattern: dòng = link/ mở drawer) */
  onRowClick?: (row: TData) => void
  /** Class dòng theo dữ liệu (highlight dòng đang chọn…) */
  rowClassName?: (row: TData) => string | undefined
  /** Dòng đang mở (vd. trong panel chi tiết): tô nền kể cả ở các cột cố định */
  isRowActive?: (row: TData) => boolean
  /** Số dòng skeleton khi loading */
  skeletonRows?: number
}

/** Ô của cột cố định phải đặc (không trong suốt) để nội dung cuộn qua không lộ
 * ra phía sau; hover/chọn/đang mở được phản chiếu lại từ `<tr>` qua group. */
const STICKY_CELL =
  "sticky z-10 bg-card group-hover/row:bg-[color-mix(in_oklab,var(--muted)_50%,var(--card))] group-data-[state=selected]/row:bg-muted group-data-[active=true]/row:bg-accent"

/** Bóng đổ ở mép cột cố định cuối cùng — chỉ hiện khi bảng đã cuộn ngang. */
const STICKY_EDGE =
  "group-data-[scrolled=true]/scroll:shadow-[6px_0_8px_-6px_rgb(0_0_0/0.18)]"

/**
 * Bảng render từ TanStack table instance (useLegacyTable) — pattern dùng
 * chung cho mọi data table của app: sticky header tuỳ chọn, cột cố định bên
 * trái (`meta.stickyLeft`), skeleton loading, empty state, row click. Toolbar/
 * pagination/lọc đi kèm ở các component riêng trong folder này.
 *
 * Chỉ MỘT vùng cuộn (div ngoài): dùng `<table>` trần thay vì `Table` của shadcn
 * (nó tự bọc thêm một `overflow-x-auto`). Vùng cuộn lồng nhau khiến thanh cuộn
 * ngang nằm tít cuối bảng và header/cột dính không bám đúng khung.
 */
export function DataTable<TData extends RowData>({
  table,
  isLoading,
  emptyContent,
  maxHeightClass,
  onRowClick,
  rowClassName,
  isRowActive,
  skeletonRows = 6,
}: DataTableProps<TData>) {
  const t = useT()
  const [scrolled, setScrolled] = useState(false)
  const rows = table.getRowModel().rows
  const columns = table.getVisibleLeafColumns()
  const columnCount = columns.length
  const sticky = Boolean(maxHeightClass)

  return (
    <div
      data-slot="data-table-scroll"
      data-scrolled={scrolled ? "true" : "false"}
      onScroll={(event) => {
        const next = event.currentTarget.scrollLeft > 0
        setScrolled((previous) => (previous === next ? previous : next))
      }}
      className={cn("group/scroll relative w-full overflow-auto", maxHeightClass)}
    >
      <table data-slot="table" className="w-full caption-bottom text-sm">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const sorted = header.column.getIsSorted()
                const meta = header.column.columnDef.meta
                const frozen = meta?.stickyLeft != null
                return (
                  <TableHead
                    key={header.id}
                    aria-sort={
                      sorted === "asc"
                        ? "ascending"
                        : sorted === "desc"
                          ? "descending"
                          : undefined
                    }
                    style={frozen ? { left: meta?.stickyLeft } : undefined}
                    className={cn(
                      sticky && "sticky top-0 z-10 bg-background",
                      // Cột cố định nằm trên cả header dính để không bị đè khi cuộn chéo.
                      frozen && "sticky z-20 bg-background",
                      meta?.stickyEdge && STICKY_EDGE,
                      meta?.thClassName,
                    )}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: skeletonRows }).map((_, i) => (
              <TableRow key={`skeleton-${i}`}>
                {columns.map((column) => (
                  <TableCell key={column.id}>
                    <Skeleton className="h-5 w-full max-w-40" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columnCount} className="py-10">
                {emptyContent ?? (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>{t.table.noResults}</EmptyTitle>
                      <EmptyDescription>
                        {t.table.noResultsHint}
                      </EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => {
              const active = isRowActive?.(row.original) ?? false
              return (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  data-active={active ? "true" : undefined}
                  className={cn(
                    "group/row",
                    onRowClick ? "cursor-pointer" : undefined,
                    active && "bg-accent hover:bg-accent",
                    rowClassName?.(row.original),
                  )}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                >
                  {row.getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta
                    const frozen = meta?.stickyLeft != null
                    return (
                      <TableCell
                        key={cell.id}
                        style={frozen ? { left: meta?.stickyLeft } : undefined}
                        className={cn(
                          frozen && STICKY_CELL,
                          meta?.stickyEdge && STICKY_EDGE,
                          meta?.tdClassName,
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    )
                  })}
                </TableRow>
              )
            })
          )}
        </TableBody>
      </table>
    </div>
  )
}

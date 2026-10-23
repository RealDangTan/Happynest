"use client"

import type { ReactNode } from "react"
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
  Table,
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
  /** Số dòng skeleton khi loading */
  skeletonRows?: number
}

/**
 * Bảng render từ TanStack table instance (useLegacyTable) — pattern dùng
 * chung cho mọi data table của app: sticky header tuỳ chọn, skeleton
 * loading, empty state, row click. Toolbar/pagination/lọc đi kèm ở các
 * component riêng trong folder này.
 */
export function DataTable<TData extends RowData>({
  table,
  isLoading,
  emptyContent,
  maxHeightClass,
  onRowClick,
  rowClassName,
  skeletonRows = 6,
}: DataTableProps<TData>) {
  const t = useT()
  const rows = table.getRowModel().rows
  const columns = table.getVisibleLeafColumns()
  const columnCount = columns.length
  const sticky = Boolean(maxHeightClass)

  return (
    <div
      data-slot="data-table-scroll"
      className={cn("relative w-full overflow-auto", maxHeightClass)}
    >
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const sorted = header.column.getIsSorted()
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
                    className={cn(
                      sticky && "sticky top-0 z-10 bg-background",
                      header.column.columnDef.meta?.thClassName,
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
            rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() ? "selected" : undefined}
                className={cn(
                  onRowClick ? "cursor-pointer" : undefined,
                  rowClassName?.(row.original),
                )}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={cell.column.columnDef.meta?.tdClassName}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

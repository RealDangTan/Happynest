"use client"

import { ArrowDown, ArrowUp, ChevronsUpDown, EyeOff } from "lucide-react"
import type { LegacyColumn } from "@tanstack/react-table/legacy"
import type { RowData } from "@tanstack/react-table"
import { useT } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

type DataTableColumnHeaderProps<TData extends RowData, TValue> = {
  column: LegacyColumn<TData, TValue>
  title: string
  className?: string
}

/**
 * Header cột sắp xếp được (pattern shadcn): cả nút mở menu asc/desc/bỏ sắp
 * xếp/ẩn cột; icon hướng hiển thị trạng thái, chevron mờ chỉ hiện khi hover
 * để toolbar nhìn gọn.
 */
export function DataTableColumnHeader<TData extends RowData, TValue>({
  column,
  title,
  className,
}: DataTableColumnHeaderProps<TData, TValue>) {
  const t = useT()

  if (!column.getCanSort()) {
    return <span className={cn("text-sm font-medium", className)}>{title}</span>
  }

  const sorted = column.getIsSorted()

  return (
    <div className={cn("flex items-center", className)}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="group -ml-2.5 gap-1.5 data-[state=open]:bg-accent"
          >
            <span>{title}</span>
            {sorted === "asc" ? (
              <ArrowUp data-icon="inline-end" />
            ) : sorted === "desc" ? (
              <ArrowDown data-icon="inline-end" />
            ) : (
              <ChevronsUpDown
                data-icon="inline-end"
                className="opacity-0 transition-opacity group-hover:opacity-100"
              />
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={() => column.toggleSorting(false)}>
            <ArrowUp data-icon="inline-start" />
            {t.table.sortAsc}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => column.toggleSorting(true)}>
            <ArrowDown data-icon="inline-start" />
            {t.table.sortDesc}
          </DropdownMenuItem>
          {sorted ? (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => column.clearSorting()}>
                <ChevronsUpDown data-icon="inline-start" />
                {t.table.sortClear}
              </DropdownMenuItem>
            </>
          ) : null}
          {column.getCanHide() ? (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => column.toggleVisibility(false)}>
                <EyeOff data-icon="inline-start" />
                {t.table.columns}
              </DropdownMenuItem>
            </>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

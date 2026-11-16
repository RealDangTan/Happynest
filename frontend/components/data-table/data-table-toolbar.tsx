"use client"

import type { ReactNode } from "react"
import { useState } from "react"
import type { LegacyReactTable } from "@tanstack/react-table/legacy"
import type { RowData } from "@tanstack/react-table"
import { Columns3, Search, X } from "lucide-react"
import { useT } from "@/lib/i18n"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { FacetedFilterConfig } from "./types"
import { DataTableFacetedFilter } from "./data-table-faceted-filter"

type DataTableToolbarProps<TData extends RowData> = {
  table: LegacyReactTable<TData>
  /** Search toàn cục. Bỏ qua prop → không hiện ô search. */
  search?:
    | { placeholder?: string }
    /** Chế độ controlled (server-side search): value + onChange từ trang. */
    | { placeholder?: string; value: string; onChange: (v: string) => void }
  /** Faceted filters theo cột */
  filters?: FacetedFilterConfig[]
  /** Ẩn menu chọn cột (mặc định hiện) */
  hideColumnToggle?: boolean
  /** Nút "Mặc định" của menu cột. Bỏ trống → bật hiện mọi cột (hành vi cũ);
   * trang có cột mặc định ẩn (vd. metadata) truyền hàm để quay về đúng mặc định. */
  onResetColumns?: () => void
  /** Slot controls riêng của trang (select import, actions…) */
  children?: ReactNode
}

/**
 * Toolbar một hàng gọn: search + faceted filters + controls riêng của trang
 * bên trái, nút xoá filter + chọn cột bên phải (icon). Không nhồi mọi thứ
 * ra UI — filter đang bật mới hiện nút reset.
 */
export function DataTableToolbar<TData extends RowData>({
  table,
  search,
  filters,
  hideColumnToggle,
  onResetColumns,
  children,
}: DataTableToolbarProps<TData>) {
  const t = useT()
  const [localQuery, setLocalQuery] = useState("")
  const controlled = search != null && "value" in search ? search : null
  const query = controlled ? controlled.value : localQuery

  function setQuery(next: string) {
    if (controlled) controlled.onChange(next)
    else {
      setLocalQuery(next)
      table.setGlobalFilter(next)
    }
  }

  const isFiltered =
    table.state.columnFilters.length > 0 || query.trim() !== ""

  const toggleableColumns = table
    .getAllLeafColumns()
    .filter((c) => c.getCanHide())
  // Cột có `meta.group` (vd. metadata của file nhập) gom thành nhóm riêng dưới
  // các cột chính, mỗi nhóm một nhãn có số cột đang bật/tổng.
  const mainColumns = toggleableColumns.filter((c) => !c.columnDef.meta?.group)
  const columnGroups = [
    ...new Set(
      toggleableColumns
        .map((c) => c.columnDef.meta?.group)
        .filter((g): g is string => Boolean(g)),
    ),
  ]

  const renderColumnItem = (column: (typeof toggleableColumns)[number]) => (
    <DropdownMenuCheckboxItem
      key={column.id}
      checked={column.getIsVisible()}
      onCheckedChange={(value) => column.toggleVisibility(!!value)}
      onSelect={(e) => e.preventDefault()}
    >
      {column.columnDef.meta?.label ?? column.id}
    </DropdownMenuCheckboxItem>
  )

  return (
    <div className="flex flex-wrap items-center gap-2">
      {search ? (
        <InputGroup className="min-w-44 flex-1 sm:max-w-64">
          <InputGroupAddon>
            <Search />
          </InputGroupAddon>
          <InputGroupInput
            placeholder={search.placeholder ?? t.table.searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={search.placeholder ?? t.table.searchPlaceholder}
          />
          {query ? (
            <InputGroupAddon align="inline-end">
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t.table.clearAll}
                onClick={() => setQuery("")}
              >
                <X />
              </Button>
            </InputGroupAddon>
          ) : null}
        </InputGroup>
      ) : null}
      {filters?.map((filter) => {
        const column = table.getColumn(filter.columnId)
        if (!column) return null
        return (
          <DataTableFacetedFilter
            key={filter.columnId}
            column={column as never}
            title={filter.title}
            options={filter.options}
          />
        )
      })}
      {children}
      <div className="ml-auto flex items-center gap-2">
        {isFiltered ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              table.resetColumnFilters()
              setQuery("")
            }}
          >
            <X data-icon="inline-start" />
            {t.table.resetFilters}
          </Button>
        ) : null}
        {!hideColumnToggle && toggleableColumns.length > 0 ? (
          <DropdownMenu>
            <Tooltip>
              <TooltipTrigger asChild>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    aria-label={t.table.columnsLabel}
                  >
                    <Columns3 />
                  </Button>
                </DropdownMenuTrigger>
              </TooltipTrigger>
              <TooltipContent>{t.table.columnsLabel}</TooltipContent>
            </Tooltip>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>{t.table.columns}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {mainColumns.map(renderColumnItem)}
              {columnGroups.map((group) => {
                const inGroup = toggleableColumns.filter(
                  (c) => c.columnDef.meta?.group === group,
                )
                const shown = inGroup.filter((c) => c.getIsVisible()).length
                return (
                  <div key={group}>
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel className="flex items-center justify-between text-xs text-muted-foreground">
                      {group}
                      <span className="font-mono">
                        {shown}/{inGroup.length}
                      </span>
                    </DropdownMenuLabel>
                    {inGroup.map(renderColumnItem)}
                  </div>
                )
              })}
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                checked={false}
                onCheckedChange={() => {
                  if (onResetColumns) onResetColumns()
                  else
                    for (const column of toggleableColumns)
                      column.toggleVisibility(true)
                }}
                onSelect={(e) => e.preventDefault()}
              >
                {t.table.resetColumns}
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
    </div>
  )
}

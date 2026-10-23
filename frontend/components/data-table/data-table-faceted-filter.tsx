"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import type { LegacyColumn } from "@tanstack/react-table/legacy"
import type { RowData } from "@tanstack/react-table"
import { useT } from "@/lib/i18n"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import type { FacetedFilterOption } from "./types"

type DataTableFacetedFilterProps<TData extends RowData, TValue> = {
  column: LegacyColumn<TData, TValue>
  title: string
  options: FacetedFilterOption[]
}

/**
 * Faceted filter đa chọn (pattern NN/g + shadcn): nút outline khi mở Popover
 * danh sách checkbox kèm số lượng facet; badge đếm trên nút cho biết filter
 * đang bật. Options tĩnh (server-side table không có facet toàn cục).
 */
export function DataTableFacetedFilter<TData extends RowData, TValue>({
  column,
  title,
  options,
}: DataTableFacetedFilterProps<TData, TValue>) {
  const t = useT()
  const [query, setQuery] = useState("")
  const selected = new Set(
    (column.getFilterValue() as string[] | undefined) ?? [],
  )
  const facets = (() => {
    try {
      return column.getFacetedUniqueValues() ?? new Map<unknown, number>()
    } catch {
      return new Map<unknown, number>()
    }
  })()

  const visible =
    query.trim() === ""
      ? options
      : options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()))

  function toggle(value: string, checked: boolean) {
    const next = new Set(selected)
    if (checked) next.add(value)
    else next.delete(value)
    column.setFilterValue(next.size > 0 ? [...next] : undefined)
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          {title}
          {selected.size > 0 ? (
            <span className="rounded-sm bg-secondary px-1 font-mono text-xs tabular-nums">
              {selected.size}
            </span>
          ) : null}
          <ChevronDown data-icon="inline-end" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-52 p-0" align="start">
        {options.length > 6 ? (
          <div className="border-b p-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.table.searchPlaceholder}
              className="h-8"
            />
          </div>
        ) : null}
        <div className="max-h-64 overflow-y-auto p-1">
          {visible.map((option) => {
            const count = facets.get(option.value)
            return (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-accent"
              >
                <Checkbox
                  checked={selected.has(option.value)}
                  onCheckedChange={(checked) =>
                    toggle(option.value, checked === true)
                  }
                />
                <span className="min-w-0 flex-1 truncate">{option.label}</span>
                {typeof count === "number" && count > 0 ? (
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {count}
                  </span>
                ) : null}
              </label>
            )
          })}
          {visible.length === 0 ? (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">
              {t.table.searchNoResults}
            </p>
          ) : null}
        </div>
        {selected.size > 0 ? (
          <div className="border-t p-1">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => column.setFilterValue(undefined)}
            >
              {t.table.clearAll}
            </Button>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}

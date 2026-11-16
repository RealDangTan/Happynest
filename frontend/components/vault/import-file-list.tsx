"use client"
import { useMemo, useState } from "react"
import { FileSpreadsheet, Layers, Search, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDate, formatRelative } from "@/lib/format"
import { IMPORT_STATUS_TONE } from "@/lib/tone"
import type { ImportRecord } from "@/lib/types"
import { cn } from "@/lib/utils"

/** Từ ngần này file trở lên mới hiện ô lọc — danh sách ngắn không cần. */
const FILTER_THRESHOLD = 8

function rowCountOf(item: ImportRecord): number | null {
  return item.source_row_count ?? item.row_count
}

function RowShell({
  active,
  children,
}: {
  active: boolean
  children: React.ReactNode
}) {
  return (
    <div
      className={cn(
        "group relative flex items-center rounded-md pr-1 transition-colors",
        // Vạch màu bên trái đánh dấu mục đang xem, dễ thấy hơn chỉ nền xám.
        "before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-leaf before:opacity-0 before:transition-opacity",
        active ? "bg-accent before:opacity-100" : "hover:bg-accent/60",
      )}
    >
      {children}
    </div>
  )
}

function FileRow({
  item,
  active,
  onSelect,
  onDelete,
}: {
  item: ImportRecord
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const name = item.original_filename ?? item.id.slice(0, 8)
  const rows = rowCountOf(item)
  return (
    <RowShell active={active}>
      <button
        type="button"
        aria-current={active ? "true" : undefined}
        onClick={onSelect}
        title={`${name} — nhập ${formatDate(item.created_at)}`}
        className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md py-1.5 pr-1 pl-2.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <FileSpreadsheet
          className={cn(
            "size-4 shrink-0",
            active ? "text-foreground" : "text-muted-foreground",
          )}
        />
        <span className="min-w-0 flex-1">
          <span className={cn("block truncate text-sm", active && "font-medium")}>
            {name}
          </span>
          <span className="block truncate text-[11px] text-muted-foreground">
            {rows != null ? `${rows} dòng · ` : ""}
            {formatRelative(item.created_at)}
          </span>
        </span>
        {item.status === "imported" ? null : (
          <Badge variant={IMPORT_STATUS_TONE[item.status] ?? "secondary"}>
            {item.status === "mapping_review" || item.status === "profile_ready"
              ? "mapping"
              : item.status}
          </Badge>
        )}
      </button>
      <button
        type="button"
        onClick={onDelete}
        className={cn(
          "rounded-md p-1.5 text-muted-foreground transition-opacity outline-none hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring",
          active ? "opacity-100" : "opacity-0 group-hover:opacity-100",
        )}
        aria-label={`Xoá lô nhập ${name}`}
        title="Xoá lô nhập"
      >
        <Trash2 className="size-3.5" />
      </button>
    </RowShell>
  )
}

/**
 * Danh sách file đã nhập: một danh sách phẳng, mới nhất lên đầu, trong một thẻ
 * riêng để cột này đọc như một nhóm. Dòng đầu "Tất cả file" gộp mọi lô (kèm
 * tổng số lô và số dòng); mỗi file hiện số dòng và thời điểm nhập để phân biệt
 * các lô trùng tên. Không suy đoán thư mục từ tên file.
 */
export function ImportFileList({
  imports,
  activeId,
  loading,
  onSelectAll,
  onSelect,
  onDelete,
}: {
  imports: ImportRecord[]
  activeId: string | null
  loading: boolean
  onSelectAll: () => void
  onSelect: (item: ImportRecord) => void
  onDelete: (item: ImportRecord) => void
}) {
  const [query, setQuery] = useState("")
  const sorted = useMemo(
    () => [...imports].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [imports],
  )
  const totalRows = useMemo(
    () => imports.reduce((sum, item) => sum + (rowCountOf(item) ?? 0), 0),
    [imports],
  )
  const q = query.trim().toLowerCase()
  const visible = q
    ? sorted.filter((item) => (item.original_filename ?? "").toLowerCase().includes(q))
    : sorted

  return (
    <aside
      aria-label="File đã nhập"
      className="flex flex-col gap-2 self-start rounded-xl border bg-card p-2 shadow-xs lg:sticky lg:top-20"
    >
      <div className="flex items-center justify-between px-2 pt-1">
        <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          File đã nhập
        </h2>
        {imports.length > 0 ? (
          <span className="font-mono text-xs text-muted-foreground">{imports.length}</span>
        ) : null}
      </div>

      {imports.length > FILTER_THRESHOLD ? (
        <InputGroup>
          <InputGroupAddon>
            <Search />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Lọc theo tên file…"
            aria-label="Lọc file đã nhập"
          />
        </InputGroup>
      ) : null}

      <ul className="flex max-h-[calc(100dvh-16rem)] flex-col gap-0.5 overflow-y-auto">
        <li>
          <RowShell active={activeId == null}>
            <button
              type="button"
              aria-pressed={activeId == null}
              onClick={onSelectAll}
              className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md py-1.5 pr-1 pl-2.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Layers
                className={cn(
                  "size-4 shrink-0",
                  activeId == null ? "text-foreground" : "text-muted-foreground",
                )}
              />
              <span className="min-w-0 flex-1">
                <span
                  className={cn("block truncate text-sm", activeId == null && "font-medium")}
                >
                  Tất cả file
                </span>
                {imports.length > 0 ? (
                  <span className="block truncate text-[11px] text-muted-foreground">
                    {imports.length} lô · {totalRows} dòng
                  </span>
                ) : null}
              </span>
            </button>
          </RowShell>
        </li>

        {loading ? (
          <li className="flex flex-col gap-2 px-2 pt-2">
            <Skeleton className="h-9" />
            <Skeleton className="h-9" />
          </li>
        ) : (
          <>
            {visible.length > 0 ? (
              <li role="separator" className="mx-2 my-1 border-t" />
            ) : null}
            {visible.map((item) => (
              <li key={item.id}>
                <FileRow
                  item={item}
                  active={activeId === item.id}
                  onSelect={() => onSelect(item)}
                  onDelete={() => onDelete(item)}
                />
              </li>
            ))}
          </>
        )}
      </ul>

      {!loading && imports.length === 0 ? (
        <p className="px-2 pb-1 text-sm text-muted-foreground">
          Chưa có file nào được nhập.
        </p>
      ) : null}
      {!loading && imports.length > 0 && visible.length === 0 ? (
        <p className="px-2 pb-1 text-sm text-muted-foreground">
          Không có file nào khớp “{query.trim()}”.
        </p>
      ) : null}
    </aside>
  )
}

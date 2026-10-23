import type { FilterFn, SortFn, SortingState } from "@tanstack/react-table"
import type { LegacyFeatures } from "@tanstack/react-table/legacy"

/** Thứ tự ngữ nghĩa severity: low < medium < high < critical (sort alphabet
 * sẽ đẩy "low" lên trước "medium" nhưng nhầm "critical" xuống cuối). */
export const SEVERITY_RANK: Record<string, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

export function severityRank(value: unknown): number {
  return SEVERITY_RANK[String(value ?? "")] ?? 0
}

/** SortFn severity — asc = low→critical, desc = critical trước.
 * TData `any` có chủ đích: FilterFn/SortFn v9 bất biến theo TData nên dùng
 * RowData sẽ không gán được vào từng bảng cụ thể. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const severitySortFn: SortFn<LegacyFeatures, any> = (
  rowA,
  rowB,
  columnId,
) => severityRank(rowA.getValue(columnId)) - severityRank(rowB.getValue(columnId))

/** FilterFn đa chọn cho faceted filter: filterValue = string[]. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const multiSelectFilterFn: FilterFn<LegacyFeatures, any> = (
  row,
  columnId,
  filterValue,
) => {
  if (!Array.isArray(filterValue) || filterValue.length === 0) return true
  return filterValue.includes(String(row.getValue(columnId) ?? ""))
}

/** Giá trị `sort=` backend chấp nhận (GET /api/feedbacks, 2026-10-24). */
export type FeedbackServerSort =
  | "newest"
  | "oldest"
  | "source"
  | "-source"
  | "severity"
  | "-severity"
  | "confidence"
  | "-confidence"

const SORT_BY_COLUMN: Record<string, FeedbackServerSort> = {
  occurred_at: "newest",
  source: "source",
  severity: "severity",
  confidence: "confidence",
}

/** SortingState (client) → chuỗi sort server. Chỉ dùng cột đầu tiên.
 * Quy ước: desc (critical/mới nhất/A→Z trước) = dạng dương; asc = dấu "-". */
export function sortingToServerSort(sorting: SortingState): FeedbackServerSort {
  if (sorting.length === 0) return "newest"
  const { id, desc } = sorting[0]
  if (id === "occurred_at") return desc ? "newest" : "oldest"
  const base = SORT_BY_COLUMN[id]
  if (!base) return "newest"
  return ((desc ? "" : "-") + base) as FeedbackServerSort
}

/** Chuỗi sort server → SortingState (đọc lại từ URL param). */
export function serverSortToSorting(sort: string | undefined): SortingState {
  if (!sort) return [{ id: "occurred_at", desc: true }]
  const desc = !sort.startsWith("-")
  const base = (desc ? sort : sort.slice(1)) as FeedbackServerSort
  switch (base) {
    case "newest":
      return [{ id: "occurred_at", desc: true }]
    case "oldest":
      return [{ id: "occurred_at", desc: false }]
    case "source":
      return [{ id: "source", desc }]
    case "severity":
      return [{ id: "severity", desc }]
    case "confidence":
      return [{ id: "confidence", desc }]
    default:
      return [{ id: "occurred_at", desc: true }]
  }
}

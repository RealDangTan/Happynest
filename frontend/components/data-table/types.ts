import type { CellData, RowData, TableFeatures } from "@tanstack/table-core"

/* eslint-disable @typescript-eslint/no-unused-vars -- interface merging phải
 * mirror đúng danh sách generic của ColumnMeta (kể cả không dùng chúng). */
/**
 * Augment ColumnMeta của TanStack Table — mỗi cột khai báo được class riêng
 * cho `<th>`/`<td>` (độ rộng, canh phải số…) qua `meta: { thClassName }`.
 * Phải mirror đúng chữ ký generic (kể cả `in out`) để TS merge interface.
 */
declare module "@tanstack/table-core" {
  interface ColumnMeta<
    in out TFeatures extends TableFeatures,
    in out TData extends RowData,
    TValue extends CellData = CellData,
  > {
    thClassName?: string
    tdClassName?: string
    /** Nhãn người đọc cho menu "Cột hiển thị" (fallback: column.id) */
    label?: string
  }
}

/** Tuỳ chọn một faceted filter — value là giá trị lọc, label hiển thị. */
export type FacetedFilterOption = {
  value: string
  label: string
}

export type FacetedFilterConfig = {
  columnId: string
  title: string
  options: FacetedFilterOption[]
}

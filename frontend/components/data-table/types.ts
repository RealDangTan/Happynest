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
    /** Nhóm trong menu "Cột hiển thị" (vd. "Dữ liệu sản phẩm"); bỏ trống = nhóm chính */
    group?: string
    /** Cố định cột ở mép trái khi cuộn ngang; giá trị là khoảng cách tới mép
     * trái bảng (CSS length, cộng dồn độ rộng các cột cố định đứng trước). */
    stickyLeft?: string
    /** Cột cố định ngoài cùng bên phải: vẽ bóng đổ khi bảng đã cuộn ngang */
    stickyEdge?: boolean
  }
}

/** Tuỳ chọn một faceted filter — value là giá trị lọc, label hiển thị. */
export type FacetedFilterOption = {
  value: string
  label: string
  /** Số dòng mang giá trị này trong PHẠM VI đang xem (từ server). Bỏ trống thì
   * dùng facet của trang hiện tại, vốn không đủ khi phân trang phía server. */
  count?: number
}

export type FacetedFilterConfig = {
  columnId: string
  title: string
  options: FacetedFilterOption[]
}

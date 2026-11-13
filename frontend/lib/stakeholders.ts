import { toDepartment } from "./departments";
import type { ActionItem } from "./types";

export type StakeholderStatusFilter =
  | "all"
  | "accepted"
  | "proposed"
  | "edited"
  | "rejected";

/**
 * Lọc hành động cho màn Stakeholders.
 *
 * `status: "all"` trả MỌI trạng thái — trước đây so sánh `a.status === "all"`
 * nên luôn rỗng dù bộ đếm phòng ban vẫn > 0 (HN-010). Dưới bộ lọc "accepted",
 * hành động đang được chọn (đề xuất / đã chỉnh) vẫn hiện để không biến mất
 * ngay khi người dùng mở chi tiết.
 */
export function filterStakeholderActions(
  items: ActionItem[],
  {
    department,
    status,
    selectedId,
  }: {
    department: string;
    status: StakeholderStatusFilter;
    selectedId: string | null;
  },
): ActionItem[] {
  return items.filter((a) => {
    if (department !== "all" && toDepartment(a.function) !== department)
      return false;
    if (status === "all" || a.status === status) return true;
    return (
      status === "accepted" &&
      a.id === selectedId &&
      (a.status === "edited" || a.status === "proposed")
    );
  });
}

/** Số hành động theo từng trạng thái — nuôi nhãn bộ lọc và gợi ý ở empty state. */
export function countByStatus(items: ActionItem[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const a of items) counts[a.status] = (counts[a.status] ?? 0) + 1;
  return counts;
}

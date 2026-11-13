import { evidenceText } from "@/lib/evidence";

export const TOOL_LABELS: Record<string, string> = {
  get_schema: "Kiểm tra dữ liệu", profile_field: "Kiểm tra độ phủ",
  aggregate_feedback: "Tổng hợp phản hồi", compare_periods: "So sánh theo thời gian",
  segment_feedback: "So sánh các nhóm", semantic_search: "Tìm phản hồi liên quan",
  representative_feedback: "Đọc phản hồi tiêu biểu", inspect_cluster: "Xem nhóm vấn đề",
  search_similar_cases: "Đối chiếu kết luận trước",
};

/** Bản một dòng của bằng chứng — xem `lib/evidence.ts` (đọc được cả JSON bị
 * cắt cụt). Màn có chỗ hiển thị đầy đủ dùng `EvidenceCard`. */
export function readableEvidence(statement: string): string {
  return evidenceText(statement);
}

/** Thời gian đã chạy dạng m:ss. */
export function formatElapsed(fromIso: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(fromIso).getTime()) / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Sau ngưỡng này cuộc điều tra được coi là lâu hơn thường lệ. */
export const SLOW_INVESTIGATION_MS = 3 * 60_000;

export function isSlowInvestigation(fromIso: string | null | undefined, now: number): boolean {
  if (!fromIso) return false;
  return now - new Date(fromIso).getTime() >= SLOW_INVESTIGATION_MS;
}

export function restoreSession<T>(raw: string | null, productId: string | null, fallback: T): T {
  if (!raw || !productId) return fallback;
  try {
    const data = JSON.parse(raw);
    return data.productId === productId && data.value != null ? data.value as T : fallback;
  } catch { return fallback; }
}

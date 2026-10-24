const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

export const TOOL_LABELS: Record<string, string> = {
  get_schema: "Kiểm tra dữ liệu", profile_field: "Kiểm tra độ phủ",
  aggregate_feedback: "Tổng hợp phản hồi", compare_periods: "So sánh theo thời gian",
  segment_feedback: "So sánh các nhóm", semantic_search: "Tìm phản hồi liên quan",
  representative_feedback: "Đọc phản hồi tiêu biểu", inspect_cluster: "Xem nhóm vấn đề",
  search_similar_cases: "Đối chiếu kết luận trước",
};

const LABELS: Record<string, string> = {
  group_by: "Nhóm theo", field: "Trường", metric: "Chỉ số", count: "Số phản hồi",
  coverage: "Độ phủ", distinct: "Giá trị khác nhau", current_count: "Kỳ hiện tại",
  previous_count: "Kỳ trước", change_pct: "Thay đổi (%)", current: "Kỳ hiện tại",
  previous: "Kỳ trước", feedback_text: "Phản hồi", statement: "Bằng chứng",
  total: "Tổng", name: "Tên", type: "Loại", value: "Giá trị",
  summary: "Tóm tắt", feedback_count: "Số phản hồi", live_member_count: "Số phản hồi hiện có",
  growth_ratio: "Mức tăng", is_emerging: "Vấn đề mới xuất hiện", is_spike: "Tăng đột biến",
  suggested_priority: "Mức ưu tiên gợi ý", severity_dist: "Mức độ nghiêm trọng",
  high: "Cao", critical: "Nghiêm trọng", medium: "Trung bình", low: "Thấp",
  source: "Nguồn", text: "Nội dung", dimensions: "Các trường dữ liệu",
};

function describe(value: unknown, depth = 0): string {
  if (value == null) return "";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value !== "object") return String(value).replace(UUID, "[tham chiếu]");
  if (Array.isArray(value)) return value.slice(0, 20).map(v => describe(v, depth + 1)).filter(Boolean).join("; ");
  const item = value as Record<string, unknown>;
  if ("value" in item && "count" in item) return `${item.value ?? "Chưa có nhãn"}: ${item.count} phản hồi`;
  return Object.entries(item).filter(([key, v]) => v != null && !/(^id$|_id$|embedding|score|avg_confidence)/.test(key))
    .map(([key, v]) => {
      if (key === "coverage" && typeof v === "number") return `Độ phủ: ${Math.round(v * 100)}%`;
      if (Array.isArray(v)) return describe(v, depth + 1);
      if (depth > 3) return "";
      return `${LABELS[key] ?? key.replaceAll("_", " ")}: ${describe(v, depth + 1)}`;
    }).filter(Boolean).join(" · ");
}

export function readableEvidence(statement: string): string {
  const match = statement.match(/^(\w+):\s*([\s\S]*)$/);
  if (match && match[1] in TOOL_LABELS) {
    try { return describe(JSON.parse(match[2])) || "Bước kiểm tra này chưa trả thêm dữ liệu."; }
    catch { return `${TOOL_LABELS[match[1]]}. Kết quả phiên cũ chưa đầy đủ để hiển thị; cần kiểm tra lại dữ liệu.`; }
  }
  return statement.replace(UUID, "[tham chiếu]");
}

export function restoreSession<T>(raw: string | null, productId: string | null, fallback: T): T {
  if (!raw || !productId) return fallback;
  try {
    const data = JSON.parse(raw);
    return data.productId === productId && data.value != null ? data.value as T : fallback;
  } catch { return fallback; }
}

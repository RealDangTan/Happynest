/**
 * Màu ngữ nghĩa dùng chung cho Badge (2026-11-03): một trạng thái luôn mang
 * cùng một màu ở mọi màn — xanh lá = xong/ổn, vàng = cần người xem,
 * xanh trời = đang chạy/thông tin, san hô = lỗi/rủi ro, tím = AI.
 */
export type BadgeTone =
  | "success"
  | "warning"
  | "info"
  | "danger"
  | "ai"
  | "secondary"
  | "outline";

export const SEVERITY_TONE: Record<string, BadgeTone> = {
  low: "info",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export const IMPORT_STATUS_TONE: Record<string, BadgeTone> = {
  profile_ready: "warning",
  mapping_generating: "info",
  mapping_review: "warning",
  importing: "info",
  imported: "success",
  failed: "danger",
  cancelled: "outline",
};

export const RUN_STATUS_TONE: Record<string, BadgeTone> = {
  running: "info",
  pending_approval: "warning",
  decision_processing: "info",
  completed: "success",
  failed: "danger",
  cancelled: "outline",
};

export const INSIGHT_STATUS_TONE: Record<string, BadgeTone> = {
  pending: "warning",
  investigating: "info",
  approved: "success",
  edited: "success",
  rejected: "danger",
};

export const ACTION_STATUS_TONE: Record<string, BadgeTone> = {
  proposed: "warning",
  edited: "info",
  accepted: "success",
  rejected: "danger",
};

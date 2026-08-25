import type { AiIssue, ReviewStatus, Sentiment, Severity } from "./types";

export const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Thấp",
  medium: "Trung bình",
  high: "Cao",
  critical: "Nghiêm trọng",
};

export const REVIEW_LABEL: Record<ReviewStatus, string> = {
  unreviewed: "Chưa duyệt",
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  edited: "Đã sửa",
  rejected: "Đã loại",
};

export const SENTIMENT_LABEL: Record<Sentiment, string> = {
  positive: "Tích cực",
  negative: "Tiêu cực",
  neutral: "Trung lập",
  mixed: "Trộn",
};

export const AI_ISSUE_LABEL: Record<AiIssue, string> = {
  hallucination: "Ảo giác",
  inaccuracy: "Thiếu chính xác",
  bias: "Thiên vị",
  safety: "An toàn",
  privacy: "Quyền riêng tư",
  performance: "Hiệu năng",
  other: "Khác",
};

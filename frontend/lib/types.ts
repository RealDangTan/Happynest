export type Severity = "low" | "medium" | "high" | "critical";
export type ReviewStatus =
  | "unreviewed"
  | "pending"
  | "approved"
  | "edited"
  | "rejected";
export type AiIssue =
  | "hallucination"
  | "inaccuracy"
  | "bias"
  | "safety"
  | "privacy"
  | "performance"
  | "other";
export type Sentiment = "positive" | "negative" | "neutral" | "mixed";

export type Feedback = {
  id: string;
  source: string;
  external_ref: string | null;
  created_at: string;
  imported_at: string;
  review_status: ReviewStatus;
  pii_detected: boolean;
  severity: Severity | null;
  categories: string[] | null;
  ai_issue: AiIssue | null;
  sentiment: Sentiment | null;
  confidence: number | null;
  requires_human_review: boolean;
  sanitized_content: string | null;
};

export type FeedbackListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: Feedback[];
};

export type ImportCsvResult = {
  imported: number;
  failed: number;
  errors: { row: number; reason: string }[];
};

export type Source = {
  id: string;
  name: string;
  description: string | null;
  isActive: boolean;
  createdAt: string;
};

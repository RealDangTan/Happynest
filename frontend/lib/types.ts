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

export type RunStatus = "running" | "completed" | "failed";

export type RunProgress = {
  id: string;
  status: RunStatus;
  processed_count: number;
  total_count: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
};

export type CorrectionResponse = Feedback & { correction_recorded: boolean };

export type ClusterItem = {
  id: string;
  name: string;
  summary: string;
  feedback_count: number;
  first_seen: string;
  last_seen: string;
  current_count: number;
  previous_count: number;
  growth_ratio: number;
  is_emerging: boolean;
  is_spike: boolean;
  suggested_priority: number | null;
  sample_feedback_ids: string[];
};

export type ClusterRunResult = {
  clusters_upserted: number;
  assigned_count: number;
  unassigned_count: number;
  duration_ms: number;
};

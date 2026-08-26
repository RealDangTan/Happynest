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

export type EvidenceItem = {
  feedback_id: string;
  snippet: string;
  severity: Severity | null;
  created_at: string;
};

export type InsightItem = {
  id: string;
  cluster_id: string | null;
  title: string;
  summary: string;
  suggested_action: string;
  review_status: ReviewStatus;
  evidence: EvidenceItem[];
};

export type InsightsListResponse = { items: InsightItem[] };

/** C6 + `skipped` ngoài hợp đồng (BE được phép thêm field). */
export type InsightsRunResult = {
  insights_generated: number;
  duration_ms: number;
  skipped: number;
};

/** C4 — emerging là shape con của C1, đủ trường như ClusterItem. */
export type EmergingClusterItem = ClusterItem;

export type ReportSummary = {
  generated_at: string;
  window_days: number;
  totals: {
    feedback_count: number;
    pending_review_count: number;
    pii_detected_count: number;
  };
  /** key luôn đủ 4 mức low/medium/high/critical */
  by_severity: Partial<Record<Severity, number>>;
  /** render theo Object.entries — server trả 4 key gồm mixed (decisions 2026-08-26) */
  by_sentiment: Record<string, number>;
  top_categories: { category: string; count: number }[];
  emerging: EmergingClusterItem[];
};

export type Severity = "low" | "medium" | "high" | "critical";
export type Sentiment = "positive" | "negative" | "neutral" | "mixed";

/** ai_analysis JSONB — pipeline ghi sau classify (VoC OS §17). */
export type AiAnalysis = {
  topics: string[] | null;
  ai_issue: string | null;
  sentiment: Sentiment | null;
  severity: Severity | null;
  safety_issue: boolean | null;
  confidence: number | null;
  rationale: string | null;
  analysis_version: string | null;
};

/** Shape MỚI sau reshape VoC OS (plan 21) — feedbacks JSONB zones. */
export type Feedback = {
  id: string;
  product_id: string;
  import_id: string | null;
  source: string;
  source_record_id: string | null;
  occurred_at: string;
  imported_at: string;
  feedback_text: string | null;
  pii_detected: boolean;
  data: Record<string, string>;
  source_meta: Record<string, string>;
  ai_analysis: AiAnalysis | null;
  created_at: string;
};

export type FeedbackListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: Feedback[];
};

// ------------------------------------------------------------------ LISTEN

export type Product = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
};

export type ProductListResponse = { items: Product[]; total: number };

export type ImportStatus = "pending" | "mapping_review" | "imported" | "failed";

export type ImportRecord = {
  id: string;
  product_id: string;
  source_type: string;
  storage_path: string | null;
  mapping_version: string | null;
  schema_version: number | null;
  status: ImportStatus;
  row_count: number | null;
  error: string | null;
  created_at: string;
};

export type CandidateField = {
  key: string;
  label: string;
  description: string | null;
  type: "category" | "numeric" | "datetime" | "text" | "boolean";
};

export type MappingDecisionValue =
  | "MAP"
  | "PROMOTE"
  | "SOURCE_META"
  | "IGNORE"
  | "AMBIGUOUS";

/** 1 dòng proposal của LLM mapper (VoC OS §11). */
export type MappingItem = {
  source_field: string;
  decision: MappingDecisionValue;
  target: string | null;
  candidate: CandidateField | null;
  confidence: number;
  reason: string;
  needs_human_review: boolean;
};

export type MappingProposal = { mappings: MappingItem[] };

/** Quyết định human per source_field — Gate #1 (VoC OS §12). */
export type HumanMappingAction = "approve" | "remap" | "promote" | "demote" | "ignore";

export type MappingDecision = {
  source_field: string;
  action: HumanMappingAction;
  target_key?: string | null;
  candidate?: CandidateField | null;
};

export type ImportApplyReport = {
  import_id: string;
  imported: number;
  failed: number;
  errors: { row: number; reason: string }[];
  schema_version: number | null;
};

// ------------------------------------------------------------------ analysis

export type RunStatus = "running" | "completed" | "failed";

export type RunProgress = {
  id: string;
  status: RunStatus;
  processed_count: number;
  total_count: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  pipeline_version: string;
  llm_model: string;
  prompt_version: string;
  embedding_model: string;
};

// ------------------------------------------------------------------ insights (UNDERSTAND shape)

export type InsightEvidenceRef = {
  evidence_id: string;
  statement: string;
  source_tool: string;
};

export type InsightItem = {
  id: string;
  product_id: string;
  run_id: string | null;
  title: string;
  finding: string;
  finding_confidence: number;
  hypothesis: { statement: string | null; confidence: number | null } | null;
  affected_context: Record<string, unknown>;
  impact: string[];
  limitations: string[];
  evidence: InsightEvidenceRef[];
  status: "pending" | "approved" | "edited" | "rejected" | "investigating";
  created_at: string;
};

export type InsightsListResponse = { items: InsightItem[]; total: number };

// ------------------------------------------------------------------ clusters + reports (giữ nguyên)

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

/** C4 — emerging là shape con của C1, đủ trường như ClusterItem. */
export type EmergingClusterItem = ClusterItem;

export type ReportSummary = {
  generated_at: string;
  window_days: number;
  totals: {
    feedback_count: number;
    pii_detected_count: number;
  };
  /** key luôn đủ 4 mức low/medium/high/critical */
  by_severity: Partial<Record<Severity, number>>;
  /** render theo Object.entries — server trả 4 key gồm mixed */
  by_sentiment: Record<string, number>;
  top_categories: { category: string; count: number }[];
  emerging: EmergingClusterItem[];
};

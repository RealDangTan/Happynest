export type Severity = "low" | "medium" | "high" | "critical";
export type Sentiment = "positive" | "negative" | "neutral" | "mixed";
export type Emotion =
  | "frustration"
  | "anger"
  | "disappointment"
  | "confusion"
  | "anxiety"
  | "satisfaction"
  | "delight"
  | "neutral";
export type Intent =
  | "bug_report"
  | "feature_request"
  | "question"
  | "complaint"
  | "praise"
  | "other";

/** Score có kèm xác suất — enrich v3 (spec Listen 2026-10-07). */
export type LabelScore = { id?: string; label?: string; probability: number };

/** ai_analysis JSONB — enrich v3 ghi (spec Listen 2026-10-07, plans 31–32). */
export type AiAnalysis = {
  topics: string[] | null;
  /** probability từng topic — enrich v3; rỗng với dataset cũ */
  topic_scores?: LabelScore[] | null;
  topic_confidence?: number | null;
  uncategorized?: boolean | null;
  emotions?: string[] | null;
  emotion_scores?: LabelScore[] | null;
  intent?: Intent | null;
  ai_issue: string | null;
  sentiment: Sentiment | null;
  severity: Severity | null;
  safety_issue: boolean | null;
  confidence: number | null;
  rationale: string | null;
  taxonomy_version?: number | null;
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
  /** bump mỗi lần human apply taxonomy (plan 31) */
  taxonomy_version?: number;
  created_at: string;
};

export type ProductListResponse = { items: Product[]; total: number };

// ------------------------------------------------------------- taxonomy (plans 31/34)

export type TaxonomyNode = {
  id: string;
  product_id: string;
  parent_id: string | null;
  name: string;
  /** id ổn định cho topic label — bất biến khi rename */
  slug: string | null;
  description: string | null;
  kind: "canonical" | "emerging";
  status: "active" | "pending_review" | "merged" | "rejected";
  evidence_count: number;
  first_seen: string | null;
  last_seen: string | null;
  created_at: string;
};

export type TaxonomyListResponse = { items: TaxonomyNode[]; total: number };

/** Một node trong proposal PHẲNG của GPT — parent là NAME của topic khác. */
export type ProposedTopic = {
  name: string;
  parent: string | null;
  description?: string | null;
  /** FE-only: trạng thái chọn khi review (mặc định true) */
  selected?: boolean;
};

export type TaxonomyProposal = { topics: ProposedTopic[] };

export type TaxonomyGenerateRequest = {
  product_id: string;
  sample_size?: number;
  product_type?: string | null;
  use_case?: string | null;
  persona?: string | null;
};

export type TaxonomyGenerateResponse = {
  product_id: string;
  sample_count: number;
  proposal: TaxonomyProposal;
};

export type TaxonomyApplyResponse = {
  created: TaxonomyNode[];
  skipped: number;
  taxonomy_version: number;
};

export type TopicRecommendation = {
  name: string;
  parent: string | null;
  evidence_count: number;
  examples: string[];
  /** FE-only: trạng thái chọn khi review */
  selected?: boolean;
};

export type TopicRecommendResponse = {
  product_id: string;
  pool_count: number;
  recommendations: TopicRecommendation[];
};

export type ReEnrichResponse = { released: number; hint: string };

export type ImportStatus =
  | "pending"
  | "profile_ready"
  | "mapping_generating"
  | "mapping_review"
  | "importing"
  | "imported"
  | "failed"
  | "cancelled";

export type ImportRecord = {
  id: string;
  product_id: string;
  source_type: string;
  storage_path: string | null;
  original_filename: string | null;
  mapping_version: string | null;
  schema_version: number | null;
  status: ImportStatus;
  row_count: number | null;
  source_row_count: number | null;
  column_profiles: ColumnProfile[] | null;
  report: ImportApplyReport | null;
  mapping_started_at: string | null;
  error: string | null;
  created_at: string;
};

export type ColumnProfile = {
  name: string;
  detected_type?: string;
  null_ratio?: number;
  unique_ratio?: number;
  sample_values?: string[];
  [key: string]: unknown;
};

export type ImportPreview = {
  id: string;
  original_filename: string | null;
  source_row_count: number;
  column_profiles: ColumnProfile[];
};

export type ImportListResponse = {
  items: ImportRecord[];
  total: number;
  limit: number;
  offset: number;
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

export type RunStatus = "running" | "completed" | "failed" | "cancelled";

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
  import_id: string | null;
  mode: "selected" | "batch" | null;
  chunk_size: number;
  failed_count: number;
  cancel_requested_at: string | null;
};

export type RunListResponse = { items: RunProgress[]; total: number };

export type SelectedAnalysisScope = {
  mode: "selected";
  import_id: string;
  feedback_ids: string[];
};

export type BatchAnalysisScope = {
  mode: "batch";
  import_id: string;
};

export type AnalysisScope = SelectedAnalysisScope | BatchAnalysisScope;

export type AnalysisCostPreview = {
  eligible_count: number;
  selected_count: number;
  remaining_count: number;
  estimated_input_tokens: number;
  logical_classify_requests: number;
  logical_embedding_requests: number;
  max_provider_attempts: number;
  chunk_size: number;
};

export type ActivityState =
  | "idle"
  | "needs_attention"
  | "running"
  | "failed"
  | "completed";

export type ActivityRef =
  | { kind: "import"; id: string }
  | { kind: "run"; id: string };

export type ActivitySummary = {
  state: ActivityState;
  attentionCount: number;
  runningCount: number;
  primaryActivity: ActivityRef | null;
};

// ------------------------------------------------------------------ agent (UNDERSTAND graph)

export type AgentRunStatus =
  | "running"
  | "pending_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type InsightDraft = {
  title: string;
  finding: string;
  finding_confidence: number;
  hypothesis_statement?: string | null;
  hypothesis_confidence?: number | null;
  affected_context: Record<string, unknown>;
  impact: string[];
  limitations: string[];
};

export type PendingApproval = {
  insight_id: string | null;
  insight: InsightDraft;
  evidence: { evidence_id: string; statement: string }[];
  options: string[];
};

export type AgentRunProgress = {
  iteration: number;
  max_iterations: number;
  last_tool: string | null;
  llm_calls_used: number;
  llm_budget: number;
  evidence_count: number;
};

/** Metadata-only trace row (HAX G4/G16) — no prompt/response ever. */
export type AgentTraceRow = {
  call_type: string;
  status: "ok" | "error";
  latency_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  model: string;
  prompt_version: string;
  error: string | null;
  created_at: string;
};

export type AgentTraceResponse = {
  run_id: string;
  items: AgentTraceRow[];
};

export type AgentRunStatusResponse = {
  run_id: string;
  status: string;
  error: string | null;
  pipeline_version: string;
  started_at: string;
  completed_at: string | null;
  pending_approval: PendingApproval | null;
  progress?: AgentRunProgress | null;
};

export type AgentDecision = "approve" | "edit" | "investigate_more" | "reject";

// ------------------------------------------------------------------ actions (ACT shape)

export type BusinessFunction =
  | "MARKETING"
  | "LEGAL"
  | "DESIGN"
  | "FINANCE"
  | "ENGINEERING"
  | "OPERATION"
  | "SALES"
  | "SUPPORT";

export type ActionStatus = "proposed" | "edited" | "accepted" | "rejected";

export type ActionItem = {
  id: string;
  insight_id: string;
  function: BusinessFunction;
  recommendation: string;
  rationale: string;
  impact: number;
  effort: number;
  urgency: number;
  confidence: number;
  priority_score: number;
  human_impact: number | null;
  human_effort: number | null;
  human_urgency: number | null;
  override_reason: string | null;
  status: ActionStatus;
  created_at: string;
};

export type Quadrant = "quick_wins" | "strategic_investments" | "low_priority" | "reconsider";

export type ActionsListResponse = {
  items: ActionItem[];
  matrix: Record<Quadrant, string[]>;
};

export type ActionUpdateInput = {
  recommendation?: string;
  rationale?: string;
  impact?: number;
  effort?: number;
  urgency?: number;
  override_reason?: string;
  status?: "accepted" | "rejected";
};

export type HumanActionInput = {
  function: BusinessFunction;
  recommendation: string;
  rationale?: string;
  impact: number;
  effort: number;
  urgency: number;
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

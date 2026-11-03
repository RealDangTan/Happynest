import type { ImportRecord, InsightItem } from "@/lib/types";

/**
 * Lộ trình E2E 5 bước (plan 41): nhập → phân loại → hỏi AI & duyệt → chọn
 * hành động → bàn giao. Hàm thuần — trạng thái suy ra 100% từ dữ liệu API,
 * không lưu tiến độ ở client, nên lộ trình không bao giờ "nói dối".
 */
export const JOURNEY_STEPS = [
  "import",
  "classify",
  "investigate",
  "act",
  "handoff",
] as const;

export type JourneyStepId = (typeof JOURNEY_STEPS)[number];
export type StepStatus = "done" | "current" | "upcoming";

export type NextKind =
  | "create-product"
  | "finish-mapping"
  | "importing"
  | "import-first"
  | "classifying"
  | "build-topics"
  | "classify"
  | "reclassify"
  | "review-finding"
  | "ask"
  | "open-actions"
  | "generate-actions"
  | "decide-actions"
  | "handoff";

export type NextAction = {
  step: JourneyStepId;
  kind: NextKind;
  href: string;
  /** true = hệ thống đang làm, người dùng chỉ cần chờ (không có việc để bấm). */
  waiting: boolean;
  count?: number;
  label?: string;
  progress?: { done: number; total: number };
};

export type JourneyInput = {
  hasProduct: boolean;
  imports: Pick<ImportRecord, "id" | "status" | "original_filename" | "created_at">[];
  /** Feedback chưa phân loại trong product + import chứa mục chờ mới nhất. */
  pendingCount: number;
  pendingImportId: string | null;
  analyzedCount: number;
  runningAnalysis: {
    id: string;
    importId: string | null;
    processed: number;
    total: number;
  } | null;
  insights: Pick<InsightItem, "id" | "run_id" | "status" | "title" | "created_at">[];
  /** Hành động của kết luận đã duyệt mới nhất; null = chưa biết (đang tải). */
  actions: { insightId: string; total: number; open: number; accepted: number } | null;
  /** Số chủ đề đang hoạt động; null = chưa biết (không chặn luồng khi chưa tải). */
  topicCount: number | null;
  /** Feedback đã phân loại nhưng mang nhãn UNCATEGORIZED. */
  uncategorizedCount: number;
};

export type Journey = {
  steps: Record<JourneyStepId, { status: StepStatus; count?: number }>;
  next: NextAction;
};

const MAPPING_STATES = new Set(["profile_ready", "mapping_generating", "mapping_review"]);

const newestFirst = <T extends { created_at: string }>(items: T[]) =>
  [...items].sort((a, b) => b.created_at.localeCompare(a.created_at));

function nextAction(input: JourneyInput): NextAction {
  const imports = newestFirst(input.imports);
  const insights = newestFirst(input.insights);

  if (!input.hasProduct) {
    return { step: "import", kind: "create-product", href: "/onboarding", waiting: false };
  }

  const awaitingMapping = imports.find((i) => MAPPING_STATES.has(i.status));
  if (awaitingMapping) {
    return {
      step: "import",
      kind: "finish-mapping",
      href: `/importer?import=${awaitingMapping.id}`,
      waiting: false,
      label: awaitingMapping.original_filename ?? undefined,
    };
  }

  const importing = imports.find((i) => i.status === "importing");
  if (importing) {
    return {
      step: "import",
      kind: "importing",
      href: `/importer?import=${importing.id}`,
      waiting: true,
      label: importing.original_filename ?? undefined,
    };
  }

  const done = imports.filter((i) => i.status === "imported");
  if (done.length === 0 || input.pendingCount + input.analyzedCount === 0) {
    return { step: "import", kind: "import-first", href: "/importer?new=1", waiting: false };
  }

  if (input.runningAnalysis) {
    const run = input.runningAnalysis;
    return {
      step: "classify",
      kind: "classifying",
      href: run.importId ? `/vault?import=${run.importId}` : "/vault",
      waiting: true,
      progress: { done: run.processed, total: run.total },
    };
  }

  // Chưa có bộ chủ đề thì AI chỉ gắn được UNCATEGORIZED — tạo chủ đề trước.
  const allUncategorized =
    input.analyzedCount > 0 && input.uncategorizedCount >= input.analyzedCount;
  if (input.topicCount === 0 && (input.analyzedCount === 0 || allUncategorized)) {
    return { step: "classify", kind: "build-topics", href: "/taxonomy?generate=1", waiting: false };
  }

  // Chỉ thúc phân loại khi chưa có gì được phân loại, hoặc mục chờ thuộc file
  // vừa nhập — mục sót ở file cũ chỉ hiện số đếm trên lộ trình, không chặn bước sau.
  const freshPending =
    input.pendingCount > 0 &&
    (input.analyzedCount === 0 || input.pendingImportId === done[0]?.id);
  if (freshPending) {
    const scope = input.pendingImportId ?? done[0].id;
    return {
      step: "classify",
      kind: "classify",
      href: `/vault?import=${scope}&analyze=1`,
      waiting: false,
      count: input.pendingCount,
    };
  }

  if (allUncategorized) {
    return {
      step: "classify",
      kind: "reclassify",
      href: "/vault?reclassify=1",
      waiting: false,
      count: input.uncategorizedCount,
    };
  }

  const awaitingReview = insights.find(
    (i) => (i.status === "pending" || i.status === "investigating") && i.run_id,
  );
  if (awaitingReview) {
    return {
      step: "investigate",
      kind: "review-finding",
      href: `/data-graph?run=${awaitingReview.run_id}`,
      waiting: false,
      label: awaitingReview.title,
    };
  }

  const approved = insights.find((i) => i.status === "approved" || i.status === "edited");
  if (!approved) {
    return { step: "investigate", kind: "ask", href: "/data-graph?ask=1", waiting: false };
  }

  const matrixHref = `/matrix?report=${approved.id}`;
  const actions = input.actions?.insightId === approved.id ? input.actions : null;
  if (!actions) {
    return { step: "act", kind: "open-actions", href: matrixHref, waiting: false, label: approved.title };
  }
  if (actions.total === 0) {
    return { step: "act", kind: "generate-actions", href: matrixHref, waiting: false, label: approved.title };
  }
  if (actions.accepted === 0) {
    return { step: "act", kind: "decide-actions", href: matrixHref, waiting: false, count: actions.open };
  }
  return {
    step: "handoff",
    kind: "handoff",
    href: `/stakeholders?report=${approved.id}`,
    waiting: false,
    count: actions.accepted,
  };
}

export function deriveJourney(input: JourneyInput): Journey {
  const next = nextAction(input);
  const hasImported = input.imports.some((i) => i.status === "imported");
  const reviewCount = input.insights.filter(
    (i) => i.status === "pending" || i.status === "investigating",
  ).length;
  const hasApproved = input.insights.some(
    (i) => i.status === "approved" || i.status === "edited",
  );
  const accepted = (input.actions?.accepted ?? 0) > 0;

  const done: Record<JourneyStepId, boolean> = {
    import: hasImported && input.pendingCount + input.analyzedCount > 0,
    classify:
      input.analyzedCount > input.uncategorizedCount && !input.runningAnalysis,
    investigate: hasApproved,
    act: accepted,
    handoff: false,
  };
  const status = (id: JourneyStepId): StepStatus =>
    id === next.step ? "current" : done[id] ? "done" : "upcoming";

  return {
    next,
    steps: {
      import: { status: status("import"), count: input.pendingCount + input.analyzedCount },
      classify: { status: status("classify"), count: input.pendingCount },
      investigate: { status: status("investigate"), count: reviewCount },
      act: { status: status("act"), count: input.actions?.open ?? 0 },
      handoff: { status: status("handoff"), count: input.actions?.accepted ?? 0 },
    },
  };
}

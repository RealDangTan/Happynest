/**
 * Đọc bằng chứng của agent cho người (2026-11-03). Backend lưu mỗi bằng chứng
 * dạng `tool: {JSON kết quả}` — có thể bị cắt cụt (12000 ký tự ở run,
 * 1500 ở phân tích hành động). Module này:
 * 1. đọc JSON chịu cắt cụt: lấy được tới đâu dùng tới đó, đánh dấu `partial`;
 * 2. diễn giải từng tool thành tiêu đề, câu tóm tắt, số liệu chính, phân bố
 *    và trích dẫn phản hồi — không lộ khoá kỹ thuật, UUID hay điểm nội bộ.
 */

const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

export const TOOL_TITLES: Record<string, string> = {
  get_schema: "Kiểm tra các trường dữ liệu",
  profile_field: "Kiểm tra một trường dữ liệu",
  aggregate_feedback: "Tổng hợp phản hồi",
  compare_periods: "So sánh theo thời gian",
  segment_feedback: "So sánh các nhóm",
  semantic_search: "Tìm phản hồi liên quan",
  representative_feedback: "Đọc phản hồi tiêu biểu",
  inspect_cluster: "Xem nhóm vấn đề",
  search_similar_cases: "Đối chiếu kết luận trước",
};

const FIELD_LABELS: Record<string, string> = {
  app_version: "phiên bản ứng dụng",
  version: "phiên bản",
  source: "nguồn",
  severity: "mức độ",
  sentiment: "cảm xúc",
  topic: "chủ đề",
  topics: "chủ đề",
  category: "nhóm",
  categories: "nhóm",
  platform: "nền tảng",
  device: "thiết bị",
  os: "hệ điều hành",
  ios_version: "phiên bản iOS",
  rating: "điểm đánh giá",
  territory: "khu vực",
  country: "quốc gia",
  language: "ngôn ngữ",
  feedback_title: "tiêu đề phản hồi",
  occurred_at: "ngày phản hồi",
  ai_issue: "lỗi AI",
};

const VALUE_LABELS: Record<string, string> = {
  low: "Thấp",
  medium: "Trung bình",
  high: "Cao",
  critical: "Nghiêm trọng",
  positive: "Tích cực",
  negative: "Tiêu cực",
  neutral: "Trung lập",
  mixed: "Lẫn lộn",
  approved: "Đã duyệt",
  edited: "Đã duyệt (có sửa)",
  rejected: "Đã từ chối",
  pending: "Chờ duyệt",
};

const WINDOW_LABELS: Record<string, string> = {
  last_7_days: "7 ngày gần nhất",
  last_30_days: "30 ngày gần nhất",
  previous_7_days: "7 ngày trước đó",
  previous_30_days: "30 ngày trước đó",
};

export type EvidenceView = {
  tool: string | null;
  /** Nhãn bước kiểm tra (vd: "Tổng hợp phản hồi"); null với bằng chứng văn bản. */
  kind: string | null;
  title: string;
  summary?: string;
  facts: { label: string; value: string }[];
  bars: { label: string; count: number; share: number }[];
  /** `feedbackId` có khi công cụ trả mã phản hồi hợp lệ → giao diện mở được phản hồi gốc. */
  quotes: { text: string; meta?: string; feedbackId?: string }[];
  /** Kết quả bị rút gọn khi lưu — chỉ hiển thị phần đọc được. */
  partial: boolean;
  empty: boolean;
};

// ------------------------------------------------------------------ partial JSON

type Parsed = { value: unknown; complete: boolean };

/** Đọc JSON theo kiểu đệ quy, dừng êm khi hết chuỗi: object/array giữ các phần
 * tử đã đọc xong, chuỗi dở dang được giữ phần đã có, literal dở bị bỏ. */
export function parsePartialJson(text: string): Parsed {
  let i = 0;
  let complete = true;
  const ws = () => {
    while (i < text.length && /\s/.test(text[i])) i++;
  };
  const eof = () => i >= text.length;

  function str(): string {
    i++; // "
    let out = "";
    while (i < text.length) {
      const c = text[i];
      if (c === "\\") {
        const n = text[i + 1];
        if (n === undefined) break;
        if (n === "u") {
          const hex = text.slice(i + 2, i + 6);
          if (hex.length < 4) {
            i = text.length;
            break;
          }
          out += String.fromCharCode(parseInt(hex, 16));
          i += 6;
          continue;
        }
        out += ({ n: "\n", t: "\t", r: "\r", b: "\b", f: "\f" } as Record<string, string>)[n] ?? n;
        i += 2;
        continue;
      }
      if (c === '"') {
        i++;
        return out;
      }
      out += c;
      i++;
    }
    complete = false;
    return out ? `${out.trimEnd()}…` : out;
  }

  function literal(): unknown {
    const rest = text.slice(i);
    for (const [word, val] of [
      ["true", true],
      ["false", false],
      ["null", null],
    ] as const) {
      if (rest.startsWith(word)) {
        i += word.length;
        return val;
      }
    }
    const num = rest.match(/^-?\d+(\.\d+)?([eE][+-]?\d+)?/);
    if (num && i + num[0].length < text.length) {
      i += num[0].length;
      return Number(num[0]);
    }
    // literal/số dở dang ở cuối chuỗi
    complete = false;
    i = text.length;
    return undefined;
  }

  function value(): unknown {
    ws();
    if (eof()) {
      complete = false;
      return undefined;
    }
    const c = text[i];
    if (c === "{") return obj();
    if (c === "[") return arr();
    if (c === '"') return str();
    return literal();
  }

  function obj(): Record<string, unknown> {
    i++;
    const out: Record<string, unknown> = {};
    for (;;) {
      ws();
      if (eof()) {
        complete = false;
        return out;
      }
      if (text[i] === "}") {
        i++;
        return out;
      }
      if (text[i] === ",") {
        i++;
        continue;
      }
      if (text[i] !== '"') {
        complete = false;
        i = text.length;
        return out;
      }
      const key = str();
      ws();
      if (eof() || text[i] !== ":") {
        complete = false;
        i = text.length;
        return out;
      }
      i++;
      const v = value();
      if (v !== undefined) out[key] = v;
      if (!complete) return out;
    }
  }

  function arr(): unknown[] {
    i++;
    const out: unknown[] = [];
    for (;;) {
      ws();
      if (eof()) {
        complete = false;
        return out;
      }
      if (text[i] === "]") {
        i++;
        return out;
      }
      if (text[i] === ",") {
        i++;
        continue;
      }
      const v = value();
      if (v !== undefined) out.push(v);
      if (!complete) return out;
    }
  }

  const result = value();
  return { value: result, complete };
}

// ------------------------------------------------------------------ helpers

const clean = (s: unknown) => String(s ?? "").replace(UUID, "").replace(/\s+/g, " ").trim();
const pct = (n: unknown) => `${Math.round(Number(n) * 100)}%`;
const fieldLabel = (key: unknown) => {
  const k = String(key ?? "");
  return FIELD_LABELS[k] ?? k.replaceAll("_", " ");
};
const valueLabel = (v: unknown) => {
  if (v == null || v === "") return "Không rõ";
  const s = String(v);
  return VALUE_LABELS[s.toLowerCase()] ?? s;
};
const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
/** Chỉ nhận mã phản hồi đầy đủ (JSON bị cắt cụt có thể để lại mã dở dang). */
const feedbackIdOf = (v: unknown) =>
  typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
    ? v.toLowerCase()
    : undefined;

function toBars(rows: { label: string; count: number }[]) {
  const total = rows.reduce((sum, r) => sum + r.count, 0) || 1;
  return rows
    .filter((r) => r.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)
    .map((r) => ({ ...r, share: r.count / total }));
}

function blank(tool: string | null, title: string): EvidenceView {
  return {
    tool,
    kind: tool ? TOOL_TITLES[tool] ?? null : null,
    title,
    facts: [],
    bars: [],
    quotes: [],
    partial: false,
    empty: false,
  };
}

// ------------------------------------------------------------------ per tool

function describeTool(tool: string, data: Record<string, unknown>, view: EvidenceView) {
  switch (tool) {
    case "inspect_cluster": {
      view.title = data.name ? `Nhóm vấn đề “${clean(data.name)}”` : "Nhóm vấn đề";
      if (data.summary) view.summary = clean(data.summary);
      const count = num(data.feedback_count) ?? num(data.live_member_count);
      if (count != null) view.facts.push({ label: "Số phản hồi", value: String(count) });
      const growth = num(data.growth_ratio);
      if (growth != null)
        view.facts.push({
          label: "Mức tăng",
          value: growth === 0 ? "Không tăng" : `${growth > 0 ? "+" : ""}${Math.round(growth * 100)}%`,
        });
      if (data.is_spike === true) view.facts.push({ label: "Diễn biến", value: "Tăng đột biến" });
      else if (data.is_emerging === true) view.facts.push({ label: "Diễn biến", value: "Mới xuất hiện" });
      const prio = num(data.suggested_priority);
      if (prio != null) view.facts.push({ label: "Ưu tiên gợi ý", value: String(prio) });
      if (isObj(data.severity_dist))
        view.bars = toBars(
          Object.entries(data.severity_dist).map(([k, v]) => ({
            label: valueLabel(k),
            count: Number(v) || 0,
          })),
        );
      break;
    }
    case "aggregate_feedback": {
      const field = fieldLabel(data.group_by);
      view.title = `Phản hồi theo ${field}`;
      const rows = Array.isArray(data.rows) ? data.rows.filter(isObj) : [];
      view.bars = toBars(
        rows.map((r) => ({ label: valueLabel(r.value), count: Number(r.count) || 0 })),
      );
      const total = rows.reduce((sum, r) => sum + (Number(r.count) || 0), 0);
      if (total) view.facts.push({ label: "Tổng", value: `${total} phản hồi` });
      if (num(data.coverage) != null)
        view.summary = `${pct(data.coverage)} phản hồi có thông tin ${field}.`;
      if (data.metric === "avg_confidence")
        view.summary = `${view.summary ?? ""} Kèm độ tin cậy trung bình của AI.`.trim();
      break;
    }
    case "compare_periods": {
      const cur = num(data.current);
      const prev = num(data.previous);
      const curLabel = WINDOW_LABELS[String(data.current_window)] ?? "Kỳ hiện tại";
      const prevLabel = WINDOW_LABELS[String(data.previous_window)] ?? "Kỳ trước";
      view.title = "So sánh số phản hồi giữa hai kỳ";
      if (cur != null) view.facts.push({ label: curLabel, value: `${cur} phản hồi` });
      if (prev != null) view.facts.push({ label: prevLabel, value: `${prev} phản hồi` });
      const change = num(data.change_pct);
      if (change != null) {
        view.summary =
          prev === 0 && cur
            ? "Kỳ trước chưa có phản hồi nào nên chưa tính được mức thay đổi."
            : change === 0
              ? "Số phản hồi không đổi giữa hai kỳ."
              : `Số phản hồi ${change > 0 ? "tăng" : "giảm"} ${Math.abs(change)}% so với kỳ trước.`;
      }
      break;
    }
    case "segment_feedback": {
      view.title = "Nhóm nổi bật theo từng trường";
      if (isObj(data.segments))
        for (const [dim, seg] of Object.entries(data.segments)) {
          if (!isObj(seg)) continue;
          view.facts.push({
            label: fieldLabel(dim),
            value:
              seg.top == null
                ? "Chưa đủ dữ liệu"
                : `${valueLabel(seg.top)} (${pct(seg.share)} phản hồi)`,
          });
        }
      break;
    }
    case "semantic_search":
    case "representative_feedback": {
      view.title =
        tool === "semantic_search" ? "Phản hồi liên quan tới câu hỏi" : "Phản hồi tiêu biểu";
      const list = (Array.isArray(data.results) ? data.results : data.samples) as unknown;
      const items = Array.isArray(list) ? list.filter(isObj) : [];
      view.quotes = items
        .map((r) => ({
          text: clean(r.snippet ?? r.text),
          meta: r.source ? `Nguồn: ${clean(r.source)}` : undefined,
          feedbackId: feedbackIdOf(r.feedback_id ?? r.id),
        }))
        .filter((q) => q.text)
        .slice(0, 5);
      if (items.length) view.facts.push({ label: "Số phản hồi đọc", value: String(items.length) });
      break;
    }
    case "search_similar_cases": {
      view.title = "Kết luận trước có liên quan";
      const cases = Array.isArray(data.cases) ? data.cases.filter(isObj) : [];
      view.quotes = cases
        .map((c) => ({
          text: [clean(c.title), clean(c.finding)].filter(Boolean).join(" — "),
          meta: c.status ? valueLabel(c.status) : undefined,
        }))
        .filter((q) => q.text)
        .slice(0, 4);
      break;
    }
    case "get_schema": {
      view.title = "Các trường dữ liệu có sẵn";
      const dims = Array.isArray(data.dimensions) ? data.dimensions.filter(isObj) : [];
      view.facts = dims.slice(0, 10).map((d) => ({
        label: fieldLabel(d.field),
        value: num(d.coverage) != null ? `${pct(d.coverage)} phản hồi có` : "—",
      }));
      break;
    }
    case "profile_field": {
      const field = fieldLabel(data.field);
      view.title = `Trường ${field}`;
      if (num(data.coverage) != null) view.facts.push({ label: "Độ phủ", value: pct(data.coverage) });
      if (num(data.distinct) != null)
        view.facts.push({ label: "Số giá trị khác nhau", value: String(data.distinct) });
      if (Array.isArray(data.top_values))
        view.bars = toBars(
          data.top_values
            .filter(Array.isArray)
            .map((pair) => ({ label: valueLabel(pair[0]), count: Number(pair[1]) || 0 })),
        );
      break;
    }
    default: {
      // Tool lạ: liệt kê các giá trị đơn giản có nhãn đọc được.
      for (const [k, v] of Object.entries(data)) {
        if (/(^id$|_id$|score|embedding)/.test(k)) continue;
        if (typeof v === "string" || typeof v === "number" || typeof v === "boolean")
          view.facts.push({
            label: fieldLabel(k),
            value: typeof v === "boolean" ? (v ? "Có" : "Không") : clean(v),
          });
      }
    }
  }
}

/** Bằng chứng → mô hình hiển thị cho người đọc. */
export function parseEvidence(statement: string): EvidenceView {
  const match = statement.match(/^\s*([a-z_]+):\s*([[{][\s\S]*)$/);
  if (!match) {
    const view = blank(null, clean(statement) || "Bằng chứng");
    return view;
  }
  const tool = match[1];
  const view = blank(tool, TOOL_TITLES[tool] ?? fieldLabel(tool));
  const { value, complete } = parsePartialJson(match[2]);
  view.partial = !complete;
  if (!isObj(value) || Object.keys(value).length === 0) {
    view.empty = true;
    view.summary = "Bước kiểm tra này không trả về dữ liệu.";
    return view;
  }
  describeTool(tool, value, view);
  const nothing = !view.summary && !view.facts.length && !view.bars.length && !view.quotes.length;
  if (nothing) {
    view.empty = true;
    view.summary = view.partial
      ? "Kết quả bị rút gọn khi lưu nên chưa đọc được nội dung."
      : "Bước kiểm tra này không trả về dữ liệu.";
  }
  return view;
}

/** Bản văn bản một dòng (cho chỗ chỉ hiện chữ, vd. tooltip, xuất báo cáo). */
export function evidenceText(statement: string): string {
  const v = parseEvidence(statement);
  const parts = [v.title];
  if (v.summary) parts.push(v.summary);
  if (v.facts.length) parts.push(v.facts.map((f) => `${f.label}: ${f.value}`).join(" · "));
  if (v.bars.length) parts.push(v.bars.map((b) => `${b.label}: ${b.count}`).join(" · "));
  if (v.quotes.length) parts.push(v.quotes.map((q) => `“${q.text}”`).join(" "));
  return parts.join(". ").replace(/\.\./g, ".");
}

// Nhận cả chữ "bước"/"trường" AI viết sẵn phía trước để không thành "bước bước".
const TOOL_KEY = new RegExp(
  String.raw`(?:bước\s+|tool\s+)?\b(${Object.keys(TOOL_TITLES).join("|")})\b`,
  "gi",
);
const SNAKE_FIELD = new RegExp(
  String.raw`(?:trường\s+|field\s+)?\b(${Object.keys(FIELD_LABELS).filter((k) => k.includes("_")).join("|")})\b`,
  "gi",
);

/** Câu do AI viết (kết luận, giới hạn, ảnh hưởng) hay nhắc tên tool/trường kỹ
 * thuật — đổi sang nhãn người đọc hiểu và bỏ UUID. */
export function humanizeAgentText(text: string): string {
  return text
    .replace(TOOL_KEY, (_, key: string) => `bước “${TOOL_TITLES[key.toLowerCase()]}”`)
    .replace(SNAKE_FIELD, (_, key: string) => `trường “${FIELD_LABELS[key.toLowerCase()]}”`)
    .replace(UUID, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/** Một mục danh sách do AI trả (chuỗi hoặc object) → câu đọc được, không JSON. */
export function agentItemText(item: unknown): string {
  if (typeof item === "string") return humanizeAgentText(item);
  if (Array.isArray(item)) return item.map(agentItemText).filter(Boolean).join("; ");
  if (isObj(item))
    return Object.entries(item)
      .filter(([k, v]) => v != null && v !== "" && !/(^id$|_id$|score|embedding)/.test(k))
      .map(([, v]) => agentItemText(typeof v === "object" ? v : String(v)))
      .filter(Boolean)
      .join(" — ");
  return item == null ? "" : String(item);
}

/** Agent đôi khi chạy cùng một bước nhiều lần với cùng kết quả — gộp các bằng
 * chứng trùng nội dung thành một, giữ thứ tự xuất hiện và số lần lặp. */
export function dedupeEvidence<T extends { statement: string }>(
  items: T[],
): { item: T; repeats: number }[] {
  const seen = new Map<string, { item: T; repeats: number }>();
  for (const item of items) {
    // Gộp theo nội dung người đọc thấy, không theo chuỗi thô.
    const key = evidenceText(item.statement);
    const hit = seen.get(key);
    if (hit) hit.repeats += 1;
    else seen.set(key, { item, repeats: 1 });
  }
  return [...seen.values()];
}

/** Thông báo lỗi từ backend (vd. "ValueError: …", có UUID/JSON) → câu người
 * đọc hiểu. Lỗi mang dữ liệu thô thì nói chung chung và chỉ cách xử lý. */
export function readableError(raw: string | null | undefined): string {
  if (!raw) return "Lỗi không xác định. Hãy thử lại.";
  const text = humanizeAgentText(
    raw.replace(/^\s*[A-Za-z_.]*(Error|Exception|Timeout)[A-Za-z]*:\s*/, ""),
  );
  if (/[{[]\s*"/.test(text) || text.length > 300)
    return "Hệ thống gặp lỗi khi xử lý dữ liệu. Hãy thử lại; nếu vẫn lỗi, mở “Chi tiết kỹ thuật” để xem nguyên nhân.";
  return text;
}

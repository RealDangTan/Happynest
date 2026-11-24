import { describe, expect, it } from "vitest";
import { evidenceText, parseEvidence, parsePartialJson } from "./evidence";

// Chuỗi thật từ phần phân tích hành động — bị cắt ở 1500 ký tự giữa chừng.
const CLUSTER_CUT =
  'inspect_cluster: {"cluster_id": "03bb95ec-0bcb-4fdd-9418-495e1c793389", "name": "Lỗi đăng nhập và xác thực", "summary": "Người dùng gặp vấn đề khi đăng nhập bằng Sign in with Apple và bị loop login sau update 2.4.1.", "feedback_count": 9, "live_member_count": 9, "growth_ratio": 0.0, "is_emerging": f';
const AGGREGATE_CUT =
  'aggregate_feedback: {"group_by": "app_version", "metric": "count", "coverage": 0.5115, "rows": [{"value": null, "count": 64, "avg_confidence": null}, {"value": "2.4.1", "count": 61, "avg_confidence": null}, {"value": "2.4.0", "count": 3, "avg_confidence": null}, {"value": "2.3.8", "count": 1, "avg_c';

describe("parsePartialJson", () => {
  it("parses complete JSON", () => {
    expect(parsePartialJson('{"a": [1, 2], "b": "x"}')).toEqual({
      value: { a: [1, 2], b: "x" },
      complete: true,
    });
  });

  it("keeps everything read before the cut and flags it", () => {
    const { value, complete } = parsePartialJson('{"a": 1, "b": [1, {"c": 2}, {"d": tr');
    expect(complete).toBe(false);
    expect(value).toEqual({ a: 1, b: [1, { c: 2 }, {}] });
  });

  it("keeps a string cut mid-way with an ellipsis", () => {
    const { value } = parsePartialJson('{"summary": "Người dùng gặp vấn');
    expect(value).toEqual({ summary: "Người dùng gặp vấn…" });
  });
});

describe("parseEvidence", () => {
  it("turns a cut cluster result into a readable card", () => {
    const v = parseEvidence(CLUSTER_CUT);
    expect(v.kind).toBe("Xem nhóm vấn đề");
    expect(v.title).toBe("Nhóm vấn đề “Lỗi đăng nhập và xác thực”");
    expect(v.summary).toContain("Sign in with Apple");
    expect(v.facts).toEqual([
      { label: "Số phản hồi", value: "9" },
      { label: "Mức tăng", value: "Không tăng" },
    ]);
    expect(v.partial).toBe(true);
    expect(JSON.stringify(v)).not.toContain("03bb95ec");
  });

  it("turns a cut aggregate into a sorted distribution with plain labels", () => {
    const v = parseEvidence(AGGREGATE_CUT);
    expect(v.title).toBe("Phản hồi theo phiên bản ứng dụng");
    expect(v.summary).toBe("51% phản hồi có thông tin phiên bản ứng dụng.");
    expect(v.bars.map((b) => [b.label, b.count])).toEqual([
      ["Không rõ", 64],
      ["2.4.1", 61],
      ["2.4.0", 3],
      ["2.3.8", 1],
    ]);
    expect(evidenceText(AGGREGATE_CUT)).not.toMatch(/avg_c|group_by|aggregate_feedback/);
  });

  it("explains a period comparison in a sentence", () => {
    const v = parseEvidence(
      'compare_periods: {"current_window": "last_7_days", "previous_window": "previous_7_days", "current": 12, "previous": 8, "change_pct": 50.0}',
    );
    expect(v.summary).toBe("Số phản hồi tăng 50% so với kỳ trước.");
    expect(v.facts).toContainEqual({ label: "7 ngày gần nhất", value: "12 phản hồi" });
  });

  it("shows feedback samples as quotes with their source", () => {
    const v = parseEvidence(
      'representative_feedback: {"samples": [{"feedback_id": "f1", "source": "app-store", "text": "Face ID không hoạt động"}]}',
    );
    expect(v.quotes).toEqual([{ text: "Face ID không hoạt động", meta: "Nguồn: app-store" }]);
  });

  it("keeps a full feedback id on quotes so the source can be opened", () => {
    const id = "3ee81be3-9fdd-4b8d-9545-a844e12eaf8e";
    const v = parseEvidence(
      `semantic_search: {"results": [{"id": "${id}", "source": "app", "snippet": "Đăng nhập lỗi"}, {"id": "3ee81be3-9fdd", "snippet": "Mã bị cắt"}]}`,
    );
    expect(v.quotes[0].feedbackId).toBe(id);
    expect(v.quotes[1].feedbackId).toBeUndefined();
  });

  it("says plainly when a step returned nothing", () => {
    const v = parseEvidence("compare_periods: {}");
    expect(v.empty).toBe(true);
    expect(v.summary).toBe("Bước kiểm tra này không trả về dữ liệu.");
  });

  it("keeps plain-text evidence as is", () => {
    expect(parseEvidence("Complaints increased by 12%.").title).toBe("Complaints increased by 12%.");
  });
});

describe("dedupeEvidence", () => {
  it("merges identical results and counts repeats in first-seen order", async () => {
    const { dedupeEvidence } = await import("./evidence");
    const rows = dedupeEvidence([
      { evidence_id: "a", statement: "x: {}" },
      { evidence_id: "b", statement: "y: {}" },
      { evidence_id: "c", statement: "x: {} " },
    ]);
    expect(rows.map((r) => [r.item.evidence_id, r.repeats])).toEqual([
      ["a", 2],
      ["b", 1],
    ]);
  });
});

describe("readableError", () => {
  it("drops exception class names and keeps the message", async () => {
    const { readableError } = await import("./evidence");
    expect(readableError("ValueError: Hai cột cùng MAP vào một target — không cho phép.")).toBe(
      "Hai cột cùng MAP vào một target — không cho phép.",
    );
  });

  it("never shows raw payloads", async () => {
    const { readableError } = await import("./evidence");
    expect(readableError('LLMStructureError: {"actions": [{"function": "X"')).toContain("Hãy thử lại");
    expect(readableError(null)).toBe("Lỗi không xác định. Hãy thử lại.");
  });
});

describe("humanizeAgentText", () => {
  it("replaces tool and field identifiers in AI-written sentences", async () => {
    const { humanizeAgentText } = await import("./evidence");
    const text = humanizeAgentText(
      "compare_periods trả về dữ liệu rỗng; chỉ có 23,7% dữ liệu có feedback_title.",
    );
    expect(text).toBe(
      "bước “So sánh theo thời gian” trả về dữ liệu rỗng; chỉ có 23,7% dữ liệu có trường “tiêu đề phản hồi”.",
    );
  });

  it("does not double the word the AI already wrote", async () => {
    const { humanizeAgentText } = await import("./evidence");
    expect(humanizeAgentText("Độ phủ của trường feedback_title thấp; bước aggregate_feedback rỗng.")).toBe(
      "Độ phủ của trường “tiêu đề phản hồi” thấp; bước “Tổng hợp phản hồi” rỗng.",
    );
  });
});

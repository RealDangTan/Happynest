import { describe, expect, it } from "vitest";
import { priorityLabel, SEVERITY_LABEL, SENTIMENT_LABEL } from "./labels";

describe("priorityLabel", () => {
  it("vi: ≥0.66 → cao", () => {
    expect(priorityLabel(0.66, "vi")).toBe("cao");
    expect(priorityLabel(1, "vi")).toBe("cao");
  });

  it("vi: 0.33–<0.66 → trung bình", () => {
    expect(priorityLabel(0.33, "vi")).toBe("trung bình");
    expect(priorityLabel(0.659, "vi")).toBe("trung bình");
  });

  it("vi: <0.33 → thấp", () => {
    expect(priorityLabel(0, "vi")).toBe("thấp");
    expect(priorityLabel(0.329, "vi")).toBe("thấp");
  });

  it("en: cùng ngưỡng, nhãn tiếng Anh", () => {
    expect(priorityLabel(0.7, "en")).toBe("high");
    expect(priorityLabel(0.5, "en")).toBe("medium");
    expect(priorityLabel(0.1, "en")).toBe("low");
  });
});

describe("bộ nhãn VI/EN đầy đủ cho mọi key", () => {
  it("severity có đủ 4 mức ở cả hai ngôn ngữ", () => {
    for (const lang of ["vi", "en"] as const) {
      expect(Object.keys(SEVERITY_LABEL[lang]).sort()).toEqual([
        "critical",
        "high",
        "low",
        "medium",
      ]);
    }
  });

  it("sentiment có đủ 4 mức ở cả hai ngôn ngữ", () => {
    for (const lang of ["vi", "en"] as const) {
      expect(Object.keys(SENTIMENT_LABEL[lang]).sort()).toEqual([
        "mixed",
        "negative",
        "neutral",
        "positive",
      ]);
    }
  });
});

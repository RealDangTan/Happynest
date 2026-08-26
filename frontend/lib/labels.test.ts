import { describe, expect, it } from "vitest";
import { priorityLabel } from "./labels";

describe("priorityLabel", () => {
  it("≥0.66 → cao", () => {
    expect(priorityLabel(0.66)).toBe("cao");
    expect(priorityLabel(1)).toBe("cao");
  });

  it("0.33–<0.66 → trung bình", () => {
    expect(priorityLabel(0.33)).toBe("trung bình");
    expect(priorityLabel(0.659)).toBe("trung bình");
  });

  it("<0.33 → thấp", () => {
    expect(priorityLabel(0)).toBe("thấp");
    expect(priorityLabel(0.329)).toBe("thấp");
  });
});

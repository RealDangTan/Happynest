import { describe, expect, it } from "vitest";
import { departmentLabel, DEPARTMENTS, toDepartment } from "./departments";

describe("departments", () => {
  it("maps every BusinessFunction to a human department label", () => {
    expect(toDepartment("ENGINEERING")).toBe("engineering");
    expect(toDepartment("OPERATION")).toBe("operations");
    expect(toDepartment("SUPPORT")).toBe("support");
    expect(departmentLabel("ENGINEERING")).toBe("Engineering");
    expect(departmentLabel("OPERATION")).toBe("Operations");
  });

  it("exposes exactly the eight departments from the design brief", () => {
    expect(DEPARTMENTS).toEqual([
      "Engineering",
      "Support",
      "Design",
      "Marketing",
      "Legal",
      "Finance",
      "Operations",
      "Sales",
    ]);
  });

  it("falls back to engineering for unknown functions", () => {
    expect(toDepartment("SOMETHING" as never)).toBe("engineering");
    expect(departmentLabel("SOMETHING" as never)).toBe("Engineering");
  });
});

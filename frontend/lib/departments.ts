import type { BusinessFunction } from "./types";

/** BusinessFunction → department key used across Matrix + Stakeholders. */
export function toDepartment(fn: BusinessFunction | string): string {
  switch (fn) {
    case "MARKETING":
      return "marketing";
    case "LEGAL":
      return "legal";
    case "DESIGN":
      return "design";
    case "FINANCE":
      return "finance";
    case "ENGINEERING":
      return "engineering";
    case "OPERATION":
      return "operations";
    case "SALES":
      return "sales";
    case "SUPPORT":
      return "support";
    default:
      return "engineering";
  }
}

export const DEPARTMENTS = [
  "Engineering",
  "Support",
  "Design",
  "Marketing",
  "Legal",
  "Finance",
  "Operations",
  "Sales",
] as const;

export function departmentLabel(fn: BusinessFunction | string): string {
  const key = toDepartment(fn);
  return (DEPARTMENTS as readonly string[]).find((d) => d.toLowerCase() === key) ?? "Engineering";
}

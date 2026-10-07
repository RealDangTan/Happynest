import type { ActionItem, Quadrant } from "./types";

/** VoC OS §50 — mirrors backend `act_agent.matrix_quadrant` exactly. */
export function quadrantOf(impact: number, effort: number): Quadrant {
  const highImpact = impact >= 5;
  const lowEffort = effort <= 5;
  if (highImpact && lowEffort) return "quick_wins";
  if (highImpact) return "strategic_investments";
  if (lowEffort) return "low_priority";
  return "reconsider";
}

/** Effective = human override when present, agent value otherwise (§51). */
export function effectiveScores(action: ActionItem): {
  impact: number;
  effort: number;
  urgency: number;
} {
  return {
    impact: action.human_impact ?? action.impact,
    effort: action.human_effort ?? action.effort,
    urgency: action.human_urgency ?? action.urgency,
  };
}

export const QUADRANT_LABEL: Record<Quadrant, string> = {
  quick_wins: "Quick wins",
  strategic_investments: "Strategic investments",
  low_priority: "Low priority",
  reconsider: "Reconsider",
};

export const QUADRANT_POSITION: Record<Quadrant, { row: 0 | 1; col: 0 | 1 }> = {
  quick_wins: { row: 0, col: 0 },
  strategic_investments: { row: 0, col: 1 },
  low_priority: { row: 1, col: 0 },
  reconsider: { row: 1, col: 1 },
};

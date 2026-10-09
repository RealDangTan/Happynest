import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { ActionItem, ActionLens } from "@/lib/types";

const LENS_LABELS: Record<ActionLens, string> = {
  product: "Product", discovery: "Discovery", engineering: "Engineering",
  ux: "User experience", risk: "Risk", customer_success: "Customer success", finance: "Finance",
};

const KIND_LABELS = {
  mitigate: "Mitigate the problem", improve: "Improve the product", investigate: "Investigate further",
};

function SupportSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

function safeSourceUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

/** The stored analysis describes the original proposal, even after Gate #3 edits. */
export function ActionDecisionSupport({ action }: {
  action: Pick<ActionItem, "recommendation" | "rationale" | "decision_support">;
}) {
  const support = action.decision_support;
  if (!support) {
    return (
      <p className="text-sm text-muted-foreground">
        No decision analysis is stored for this action. Earlier and manually added actions may not have one.
      </p>
    );
  }

  const changed = action.recommendation !== support.basis_recommendation || action.rationale !== support.basis_rationale;
  return (
    <div className="flex min-w-0 flex-col gap-5 text-sm break-words">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{KIND_LABELS[support.kind]}</Badge>
        <span className="text-xs text-muted-foreground">AI decision analysis</span>
      </div>

      {changed ? (
        <Alert>
          <AlertTitle>Analysis of the original AI proposal</AlertTitle>
          <AlertDescription>
            <p>The recommendation or rationale was edited. These references and assessments describe the original proposal:</p>
            <p>{support.basis_recommendation}</p>
            <p>{support.basis_rationale}</p>
          </AlertDescription>
        </Alert>
      ) : null}

      <SupportSection title="Internal evidence">
        {support.evidence.length ? support.evidence.map((item) => (
          <div key={item.evidence_id} className="flex flex-col gap-1 border-l-2 border-border pl-3">
            <span className="font-mono text-xs text-muted-foreground">EV-{item.evidence_id.slice(0, 8)}</span>
            <p>{item.statement}</p>
          </div>
        )) : (
          <p className="text-muted-foreground">No supporting evidence was available. This proposal is a step to investigate further.</p>
        )}
      </SupportSection>

      <SupportSection title="Perspectives considered">
        {support.perspectives.map((perspective) => (
          <div key={perspective.lens} className="flex flex-col gap-1">
            <Badge variant="outline">{LENS_LABELS[perspective.lens]}</Badge>
            <p>{perspective.assessment}</p>
          </div>
        ))}
      </SupportSection>

      <Separator />

      <SupportSection title="References and application">
        <p className="text-xs text-muted-foreground">External guidance supports the approach. Expected impact still needs validation for this product.</p>
        {support.references.map((reference) => {
          const href = safeSourceUrl(reference.url);
          return (
            <div key={reference.card_id} className="flex flex-col gap-2 rounded-lg border p-3">
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-signal underline underline-offset-4">
                  {reference.source_title}<span className="sr-only"> (opens in a new tab)</span>
                </a>
              ) : <p className="font-medium">{reference.source_title}</p>}
              <p className="text-xs text-muted-foreground">{reference.section}</p>
              <p>{reference.principle}</p>
              <p><strong>Applied here:</strong> {reference.application}</p>
              <p className="text-xs text-muted-foreground"><strong>Applies when:</strong> {reference.applies_when}</p>
              <p className="text-xs text-muted-foreground"><strong>Limits:</strong> {reference.limitations}</p>
              <p className="text-xs text-muted-foreground">Source reviewed {reference.reviewed_on}</p>
            </div>
          );
        })}
        {support.source_gap ? <p className="text-muted-foreground">{support.source_gap}</p> : null}
      </SupportSection>

      <SupportSection title="Alternative and tradeoffs">
        <p><strong>Alternative considered:</strong> {support.alternative.recommendation}</p>
        <p className="text-muted-foreground">{support.alternative.tradeoff}</p>
        <p><strong>Chosen approach:</strong> {support.tradeoff}</p>
      </SupportSection>

      <SupportSection title="Assumptions and validation">
        <ul className="flex list-disc flex-col gap-1 pl-4">
          {support.assumptions.map((assumption, index) => <li key={index}>{assumption}</li>)}
        </ul>
        <p><strong>Success criteria:</strong> {support.success_criteria}</p>
        <p><strong>Estimate basis:</strong> {support.estimate_basis}</p>
      </SupportSection>
    </div>
  );
}

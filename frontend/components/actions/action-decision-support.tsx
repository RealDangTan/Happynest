import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { EvidenceCard } from "@/components/ai/evidence-card";
import { dedupeEvidence } from "@/lib/evidence";
import type { ActionItem, ActionLens } from "@/lib/types";

const LENS_LABELS: Record<ActionLens, string> = {
  product: "Sản phẩm", discovery: "Khám phá nhu cầu", engineering: "Kỹ thuật",
  ux: "Trải nghiệm người dùng", risk: "Rủi ro", customer_success: "Chăm sóc khách hàng", finance: "Tài chính",
};

const KIND_LABELS = {
  mitigate: "Giảm thiểu vấn đề", improve: "Cải thiện sản phẩm", investigate: "Điều tra thêm",
};

const KIND_TONE = { mitigate: "danger", improve: "success", investigate: "warning" } as const;

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
        Chưa có phân tích cho hành động này. Hành động cũ hoặc do người dùng tự thêm có thể không có phần phân tích.
      </p>
    );
  }

  const changed = action.recommendation !== support.basis_recommendation || action.rationale !== support.basis_rationale;
  const evidence = dedupeEvidence(support.evidence);
  return (
    <div className="flex min-w-0 flex-col gap-5 text-sm break-words">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={KIND_TONE[support.kind]}>{KIND_LABELS[support.kind]}</Badge>
        <Badge variant="ai">Phân tích của AI</Badge>
      </div>

      {changed ? (
        <Alert>
          <AlertTitle>Phân tích dựa trên đề xuất gốc của AI</AlertTitle>
          <AlertDescription>
            <p>Nội dung hoặc lý do đã được chỉnh. Các tham chiếu và đánh giá dưới đây mô tả đề xuất ban đầu:</p>
            <p>{support.basis_recommendation}</p>
            <p>{support.basis_rationale}</p>
          </AlertDescription>
        </Alert>
      ) : null}

      <SupportSection title={`Bằng chứng từ dữ liệu (${evidence.length})`}>
        {evidence.length ? evidence.map(({ item, repeats }, i) => (
          <EvidenceCard key={item.evidence_id} statement={item.statement} index={i + 1} repeats={repeats} />
        )) : (
          <p className="text-muted-foreground">Chưa có bằng chứng hỗ trợ — đề xuất này là một bước để điều tra thêm.</p>
        )}
      </SupportSection>

      <SupportSection title="Các góc nhìn đã cân nhắc">
        {support.perspectives.map((perspective) => (
          <div key={perspective.lens} className="flex flex-col gap-1">
            <Badge variant="outline">{LENS_LABELS[perspective.lens]}</Badge>
            <p>{perspective.assessment}</p>
          </div>
        ))}
      </SupportSection>

      <Separator />

      <SupportSection title="Tham chiếu và cách áp dụng">
        <p className="text-xs text-muted-foreground">Hướng dẫn bên ngoài ủng hộ cách làm này; tác động thực tế vẫn cần kiểm chứng trên sản phẩm.</p>
        {support.references.map((reference) => {
          const href = safeSourceUrl(reference.url);
          return (
            <div key={reference.card_id} className="flex flex-col gap-2 rounded-lg border p-3">
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-signal underline underline-offset-4">
                  {reference.source_title}<span className="sr-only"> (mở tab mới)</span>
                </a>
              ) : <p className="font-medium">{reference.source_title}</p>}
              <p className="text-xs text-muted-foreground">{reference.section}</p>
              <p>{reference.principle}</p>
              <p><strong>Áp dụng ở đây:</strong> {reference.application}</p>
              <p className="text-xs text-muted-foreground"><strong>Phù hợp khi:</strong> {reference.applies_when}</p>
              <p className="text-xs text-muted-foreground"><strong>Giới hạn:</strong> {reference.limitations}</p>
              <p className="text-xs text-muted-foreground">Đã xem lại nguồn ngày {reference.reviewed_on}</p>
            </div>
          );
        })}
        {support.source_gap ? <p className="text-muted-foreground">{support.source_gap}</p> : null}
      </SupportSection>

      <SupportSection title="Phương án khác và đánh đổi">
        <p><strong>Phương án đã cân nhắc:</strong> {support.alternative.recommendation}</p>
        <p className="text-muted-foreground">{support.alternative.tradeoff}</p>
        <p><strong>Lý do chọn cách này:</strong> {support.tradeoff}</p>
      </SupportSection>

      <SupportSection title="Giả định và cách kiểm chứng">
        <ul className="flex list-disc flex-col gap-1 pl-4">
          {support.assumptions.map((assumption, index) => <li key={index}>{assumption}</li>)}
        </ul>
        <p><strong>Tiêu chí thành công:</strong> {support.success_criteria}</p>
        <p><strong>Cơ sở ước lượng:</strong> {support.estimate_basis}</p>
      </SupportSection>
    </div>
  );
}

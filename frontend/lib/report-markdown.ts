import { agentItemText, dedupeEvidence, evidenceText, humanizeAgentText } from "@/lib/evidence"
import type { InsightItem } from "@/lib/types"

export const REPORT_STATUS_LABEL: Record<InsightItem["status"], string> = {
  pending: "Chờ duyệt",
  investigating: "Đang điều tra",
  approved: "Đã duyệt",
  edited: "Đã duyệt (có sửa)",
  rejected: "Đã từ chối",
}

function plainMarkdown(value: string) {
  return value
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[\\`*_{}\[\]#|~]/g, "\\$&")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
}

export function buildReportMarkdown(
  title: string,
  product: string | undefined,
  issues: InsightItem[],
  exportedAt: Date,
) {
  const lines = [
    "# " + plainMarkdown(title),
    "",
    ...(product ? ["- **Sản phẩm:** " + plainMarkdown(product)] : []),
    "- **Số vấn đề:** " + issues.length,
    "- **Ngày xuất:** " + exportedAt.toLocaleDateString("vi-VN"),
  ]

  for (const issue of issues) {
    lines.push(
      "",
      "## " + plainMarkdown(issue.title),
      "",
      "- **Trạng thái:** " + (REPORT_STATUS_LABEL[issue.status] ?? plainMarkdown(issue.status)),
    )
    if (issue.finding_confidence != null) {
      lines.push("- **Độ tin cậy của kết luận:** " + Math.round(issue.finding_confidence * 100) + "%")
    }

    const finding = humanizeAgentText(issue.finding ?? "")
    if (finding) lines.push("", "### Kết luận", "", plainMarkdown(finding))
    if (issue.hypothesis?.statement) {
      lines.push("", "### Giả thuyết cần kiểm chứng", "", plainMarkdown(humanizeAgentText(issue.hypothesis.statement)))
      if (issue.hypothesis.confidence != null) {
        lines.push("", "Độ tin cậy: " + Math.round(issue.hypothesis.confidence * 100) + "%")
      }
    }

    const impact = (issue.impact ?? []).map(agentItemText).filter(Boolean)
    const limitations = (issue.limitations ?? []).map(agentItemText).filter(Boolean)
    if (impact.length) lines.push("", "### Ảnh hưởng", "", ...impact.map((item) => "- " + plainMarkdown(item)))
    if (limitations.length) lines.push("", "### Giới hạn", "", ...limitations.map((item) => "- " + plainMarkdown(item)))

    const evidence = dedupeEvidence(issue.evidence ?? [])
    lines.push("", "### Bằng chứng", "")
    if (!evidence.length) lines.push("Chưa ghi nhận bằng chứng.")
    for (const { item, repeats } of evidence) {
      const repeatNote = repeats > 1 ? " (" + repeats + " lần ghi nhận)" : ""
      lines.push("- " + plainMarkdown(evidenceText(item.statement)) + repeatNote)
    }
  }

  return lines.join("\n") + "\n"
}

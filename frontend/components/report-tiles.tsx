import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import type { ReportSummary } from "@/lib/types"

/** 3 stat tile tổng hợp — DÙNG CHUNG /reports và /dashboard để số liệu
 * khớp 1:1 giữa hai trang (AC dashboard). Tile "Chờ duyệt" là link thẳng
 * vào queue review. */
export function ReportTiles({ totals }: { totals: ReportSummary["totals"] }) {
  const tiles: { label: string; value: number; href?: string }[] = [
    { label: "Tổng phản hồi", value: totals.feedback_count },
    {
      label: "Chờ duyệt",
      value: totals.pending_review_count,
      href: "/feedbacks?review_status=pending",
    },
    { label: "Phát hiện PII", value: totals.pii_detected_count },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {tiles.map((t) => {
        const body = (
          <CardContent className="flex flex-col gap-1">
            <span className="text-sm text-muted-foreground">{t.label}</span>
            <span className="font-heading text-3xl tabular-nums">
              {t.value}
            </span>
          </CardContent>
        )
        return t.href ? (
          <Card key={t.label} className="transition-colors hover:bg-muted/50">
            <Link href={t.href} aria-label={`${t.label}: ${t.value}`}>
              {body}
            </Link>
          </Card>
        ) : (
          <Card key={t.label}>{body}</Card>
        )
      })}
    </div>
  )
}

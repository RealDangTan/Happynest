"use client"
import Link from "next/link"
import { useMemo } from "react"
import { ArrowRight, CircleHelp, Quote } from "lucide-react"
import { useInsights } from "@/hooks/use-insights"
import type { InsightItem } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { AiBadge } from "@/components/ai/ai-badge"
import { ConfidenceMeter } from "@/components/ai/confidence-meter"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader } from "@/components/page-header"
import { humanizeAgentText, parseEvidence } from "@/lib/evidence"
import { INSIGHT_STATUS_TONE } from "@/lib/tone"

const DICTIONARY: [string, string][] = [
  [
    "Insight",
    "Kết luận có bằng chứng do AI điều tra rút ra — tách điều dữ liệu cho thấy khỏi giả thuyết còn phải kiểm chứng.",
  ],
  [
    "Bằng chứng",
    "Kết quả từng bước kiểm tra được ghi lại — mọi insight phải truy ngược được về bằng chứng.",
  ],
]

const STATUS_LABEL: Record<InsightItem["status"], string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  edited: "Đã sửa",
  rejected: "Đã loại",
  investigating: "Đang điều tra thêm",
}

function DictionaryPopover() {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" aria-label="Giải thích thuật ngữ">
          <CircleHelp data-icon="inline-start" />
          Thuật ngữ
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96" align="end">
        <dl className="flex flex-col gap-3 text-sm">
          {DICTIONARY.map(([term, meaning]) => (
            <div key={term}>
              <dt className="font-medium">{term}</dt>
              <dd className="text-muted-foreground">{meaning}</dd>
            </div>
          ))}
        </dl>
      </PopoverContent>
    </Popover>
  )
}

function shortDay(iso: string) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })
}

function FindingRow({ insight, rank }: { insight: InsightItem; rank: number }) {
  return (
    <li className="flex gap-4 border-t py-4 first:border-t-0 first:pt-0">
      <span className="w-6 shrink-0 font-mono text-sm text-muted-foreground" aria-hidden>
        {rank}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/reports?report=${insight.id}`}
            className="font-heading text-base leading-snug hover:underline focus-visible:outline-2 focus-visible:outline-ring"
          >
            {insight.title}
          </Link>
          <Badge variant={INSIGHT_STATUS_TONE[insight.status] ?? "secondary"}>
            {STATUS_LABEL[insight.status]}
          </Badge>
        </div>
        <p className="line-clamp-3 text-sm leading-relaxed text-foreground/85">
          {humanizeAgentText(insight.finding)}
        </p>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
          <ConfidenceMeter value={insight.finding_confidence} />
          <span>{insight.evidence.length} bằng chứng</span>
          <span className="font-mono">{shortDay(insight.created_at)}</span>
        </div>
        {insight.hypothesis?.statement ? (
          <p className="border-l-2 border-pollen pl-3 text-xs text-muted-foreground">
            Giả thuyết chưa xác nhận: {humanizeAgentText(insight.hypothesis.statement)}
          </p>
        ) : null}
      </div>
    </li>
  )
}

/**
 * Insight đọc theo ba phần (mẫu Chronicle "Voice of the Customer"): phạm vi
 * dữ liệu → phát hiện chính xếp theo độ tin cậy → lời người dùng trích từ
 * bằng chứng. Chi tiết và thao tác duyệt nằm ở Báo cáo.
 */
export default function InsightsPage() {
  const insights = useInsights()
  const items = useMemo(() => insights.data?.items ?? [], [insights.data])

  const kept = useMemo(
    () =>
      items
        .filter((i) => i.status !== "rejected")
        .sort((a, b) => b.finding_confidence - a.finding_confidence),
    [items]
  )
  const quotes = useMemo(() => {
    const out: { text: string; meta?: string; insight: InsightItem }[] = []
    const seen = new Set<string>()
    for (const insight of kept) {
      for (const ev of insight.evidence) {
        for (const q of parseEvidence(ev.statement).quotes) {
          const key = q.text.trim().toLowerCase()
          if (!key || seen.has(key)) continue
          seen.add(key)
          out.push({ ...q, insight })
        }
      }
    }
    return out.slice(0, 9)
  }, [kept])

  const approved = items.filter((i) => i.status === "approved" || i.status === "edited").length
  const pending = items.filter((i) => i.status === "pending" || i.status === "investigating").length
  const evidenceTotal = kept.reduce((n, i) => n + i.evidence.length, 0)
  const days = items.map((i) => i.created_at).sort()

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Insight"
        description="Tổng hợp các kết luận có bằng chứng và lời người dùng đằng sau chúng."
        actions={<DictionaryPopover />}
      />

      {insights.isPending ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : insights.isError ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>Chưa tải được insight</EmptyTitle>
            <EmptyDescription>{insights.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : items.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>Chưa có insight nào</EmptyTitle>
            <EmptyDescription>
              Hỏi AI trong màn Điều tra. Mỗi kết luận bạn duyệt sẽ xuất hiện tại đây kèm bằng chứng.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button asChild>
              <Link href="/data-graph?ask=1">Hỏi AI</Link>
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <>
          <section aria-labelledby="insight-scope" className="rounded-xl border bg-card px-5 py-4">
            <h2 id="insight-scope" className="sr-only">
              Phạm vi
            </h2>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted-foreground">Kết luận</dt>
                <dd className="font-heading text-2xl">{items.length}</dd>
              </div>
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted-foreground">Đã duyệt</dt>
                <dd className="font-heading text-2xl text-leaf-ink">{approved}</dd>
              </div>
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted-foreground">Chờ duyệt</dt>
                <dd className="font-heading text-2xl text-sun-ink">{pending}</dd>
              </div>
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted-foreground">Khoảng thời gian</dt>
                <dd className="font-mono text-sm leading-8">
                  {shortDay(days[0] ?? "")} – {shortDay(days.at(-1) ?? "")}
                </dd>
              </div>
            </dl>
          </section>

          <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,24rem)]">
            <Card className="min-w-0">
              <CardHeader>
                <CardTitle>Phát hiện chính</CardTitle>
                <CardDescription>
                  {kept.length} kết luận còn hiệu lực, xếp theo độ tin cậy · {evidenceTotal} bằng chứng.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ol className="flex flex-col">
                  {kept.map((insight, i) => (
                    <FindingRow key={insight.id} insight={insight} rank={i + 1} />
                  ))}
                </ol>
                {kept.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Mọi kết luận đều đã bị loại.</p>
                ) : null}
              </CardContent>
            </Card>

            <Card size="sm" className="self-start lg:sticky lg:top-20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Quote className="size-4 text-signal" aria-hidden />
                  Tiếng nói người dùng
                </CardTitle>
                <CardDescription className="flex items-center gap-2">
                  Trích từ bằng chứng của các kết luận
                  <AiBadge />
                </CardDescription>
              </CardHeader>
              <CardContent>
                {quotes.length ? (
                  <ul className="flex flex-col gap-3">
                    {quotes.map((q, i) => (
                      <li key={i} className="flex flex-col gap-1 border-l-2 border-sky-line pl-3">
                        <p className="text-sm leading-relaxed">“{q.text}”</p>
                        {q.meta ? (
                          <p className="text-[11px] text-muted-foreground">{q.meta}</p>
                        ) : null}
                        <Link
                          href={`/reports?report=${q.insight.id}`}
                          className="flex min-w-0 items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                        >
                          <span className="min-w-0 truncate">Từ: {q.insight.title}</span>
                          <ArrowRight className="size-3 shrink-0" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Bằng chứng hiện có chưa kèm trích dẫn phản hồi.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

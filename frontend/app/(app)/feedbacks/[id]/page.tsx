"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import Link from "next/link"
import { useParams } from "next/navigation"
import {
  useFeedbackDetail,
  useSimilarFeedbacks,
} from "@/hooks/use-feedback-detail"
import { ApiError } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { SEVERITY_LABEL } from "@/lib/labels"
import { useAppLang } from "@/lib/i18n"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { useProduct } from "@/hooks/use-product"
import { useTaxonomy } from "@/hooks/use-taxonomy"
import { usePageTitle } from "@/hooks/use-page-title"
import { topicLabeler } from "@/lib/graph"

export default function FeedbackDetailPage() {
  usePageTitle("Chi tiết phản hồi")
  const lang = useAppLang()
  const { id } = useParams<{ id: string }>()
  const fb = useFeedbackDetail(id)
  const similar = useSimilarFeedbacks(id)

  // Chip chủ đề hiển thị nhãn tiếng Việt (name_vi) thay vì slug thô.
  const { productId } = useProduct()
  const taxonomy = useTaxonomy(productId)
  const labelTopic = topicLabeler(taxonomy.data?.items ?? [])

  if (fb.isPending)
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  if (fb.isError)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>
            {fb.error instanceof ApiError && fb.error.status === 404
              ? "Không tìm thấy phản hồi"
              : "Không tải được"}
          </EmptyTitle>
          <EmptyDescription>{fb.error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )

  const d = fb.data
  const ai = d.ai_analysis
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/feedbacks">← Danh sách</Link>
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Phản hồi · {d.source}</CardTitle>
          <CardAction className="flex flex-wrap gap-1">
            {ai?.severity ? (
              <Badge
                variant={
                  ai.severity === "critical" || ai.severity === "high"
                    ? "destructive"
                    : "secondary"
                }
              >
                {SEVERITY_LABEL[lang][ai.severity]}
              </Badge>
            ) : null}
            {ai?.sentiment ? (
              <SentimentIndicator value={ai.sentiment} />
            ) : null}
            {ai?.uncategorized ? (
              <Badge variant="outline">UNCATEGORIZED</Badge>
            ) : null}
            {d.pii_detected ? (
              <Badge variant="outline">Phát hiện PII</Badge>
            ) : null}
            {!ai ? <Badge variant="outline">Chưa phân tích</Badge> : null}
          </CardAction>
          <CardDescription>
            {formatDate(d.occurred_at)}
            {d.source_record_id ? ` · ${d.source_record_id}` : ""}
            {d.import_id ? ` · import ${d.import_id.slice(0, 8)}…` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {d.feedback_text ?? "(chưa có nội dung đã sanitize)"}
          </p>
          {ai?.rationale ? (
            <p className="text-xs text-muted-foreground">
              AI: {ai.rationale}{" "}
              {ai.analysis_version ? `(${ai.analysis_version})` : ""}
            </p>
          ) : null}
          <Separator />
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
            <dt className="text-muted-foreground">Chủ đề</dt>
            <dd className="flex flex-wrap gap-1">
              {(ai?.topics ?? []).length > 0
                ? ai!.topics!.map((t) => (
                    <Badge key={t} variant="secondary" title={t}>
                      {labelTopic(t)}
                    </Badge>
                  ))
                : "—"}
            </dd>
            <dt className="text-muted-foreground">Cảm xúc</dt>
            <dd className="flex flex-wrap gap-1">
              {(ai?.emotions ?? []).length > 0
                ? ai!.emotions!.map((e) => (
                    <Badge key={e} variant="outline">
                      {e}
                    </Badge>
                  ))
                : "—"}
            </dd>
            <dt className="text-muted-foreground">Ý định</dt>
            <dd>{ai?.intent ?? "—"}</dd>
            <dt className="text-muted-foreground">Confidence</dt>
            <dd>
              {ai?.confidence != null
                ? `${Math.round(ai.confidence * 100)}%`
                : "—"}
            </dd>
            <dt className="text-muted-foreground">An toàn</dt>
            <dd>{ai?.safety_issue ? "⚠ Có vấn đề an toàn" : "—"}</dd>
          </dl>

          {Object.keys(d.data).length > 0 ? (
            <>
              <Separator />
              <div>
                <h3 className="mb-2 text-sm font-medium">Product data</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
                  {Object.entries(d.data).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd className="break-words">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </>
          ) : null}

          {Object.keys(d.source_meta).length > 0 ? (
            <>
              <Separator />
              <div>
                <h3 className="mb-2 text-sm font-medium">Nguồn metadata</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
                  {Object.entries(d.source_meta).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd className="break-words">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-lg">Phản hồi tương tự</h2>
        {similar.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : (similar.data?.length ?? 0) === 0 ? (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>Chưa có dữ liệu tương tự</EmptyTitle>
              <EmptyDescription>
                Chạy Analysis để tạo embedding cho phản hồi này.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <div className="flex flex-col gap-2">
            {similar.data!.map((s) => (
              <Card
                key={s.id}
                size="sm"
                className="transition-colors hover:bg-accent"
              >
                <Link href={`/feedbacks/${s.id}`}>
                  <CardContent className="flex items-start justify-between gap-4">
                    <span className="line-clamp-2 flex-1 text-sm">
                      {s.snippet}
                    </span>
                    <Badge variant="secondary">
                      {Math.round(s.score * 100)}%
                    </Badge>
                  </CardContent>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

"use client"
import { SentimentIndicator } from "@/components/sentiment-indicator"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, ArrowRight, ShieldAlert } from "lucide-react"
import {
  useFeedbackDetail,
  useSimilarFeedbacks,
} from "@/hooks/use-feedback-detail"
import { ApiError } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { SEVERITY_LABEL } from "@/lib/labels"
import { SEVERITY_TONE } from "@/lib/tone"
import { useAppLang } from "@/lib/i18n"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { useProduct } from "@/hooks/use-product"
import { useTaxonomy } from "@/hooks/use-taxonomy"
import { usePageTitle } from "@/hooks/use-page-title"
import { topicLabeler } from "@/lib/graph"

function PropertyList({ entries }: { entries: [string, unknown][] }) {
  return (
    <dl className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] gap-x-3 gap-y-2 text-sm">
      {entries.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="truncate text-muted-foreground" title={k}>
            {k}
          </dt>
          <dd className="break-words">{v == null || v === "" ? "—" : String(v)}</dd>
        </div>
      ))}
    </dl>
  )
}

/**
 * Trang chi tiết một phản hồi (mẫu Productboard): nội dung và phản hồi tương tự
 * ở cột đọc chính; nguồn, nhãn AI và metadata gom vào cột thuộc tính bên phải.
 */
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
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-48 w-full" />
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    )
  if (fb.isError)
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyTitle>
            {fb.error instanceof ApiError && fb.error.status === 404
              ? "Không tìm thấy phản hồi"
              : "Chưa tải được phản hồi"}
          </EmptyTitle>
          <EmptyDescription>{fb.error.message}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button variant="outline" asChild>
            <Link href="/vault">Về Kho phản hồi</Link>
          </Button>
        </EmptyContent>
      </Empty>
    )

  const d = fb.data
  const ai = d.ai_analysis
  const exploreHref = `/data-graph?import=${d.import_id ?? ""}${
    ai?.topics?.[0] ? `&topic=${encodeURIComponent(ai.topics[0])}` : ""
  }`

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href={d.import_id ? `/vault?import=${d.import_id}&item=${d.id}` : `/vault?item=${d.id}`}>
            <ArrowLeft data-icon="inline-start" />
            Kho phản hồi
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href={exploreHref}>
            Điều tra chủ đề này
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      </div>

      <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card>
            <CardHeader>
              <p className="font-mono text-xs text-signal">F-{d.id.slice(0, 8)}</p>
              <CardTitle className="font-heading text-xl">Phản hồi từ {d.source || "nguồn chưa rõ"}</CardTitle>
              <CardDescription>{formatDate(d.occurred_at)}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <blockquote className="border-l-2 border-signal/60 pl-4 text-base leading-relaxed whitespace-pre-wrap wrap-anywhere">
                {d.feedback_text ?? "(chưa có nội dung đã ẩn thông tin cá nhân)"}
              </blockquote>
              {d.pii_detected ? (
                <Alert>
                  <ShieldAlert />
                  <AlertTitle>Đã ẩn thông tin cá nhân</AlertTitle>
                  <AlertDescription>
                    Nội dung gốc chứa dữ liệu cá nhân; bản hiển thị và bản gửi cho AI đều đã được ẩn.
                  </AlertDescription>
                </Alert>
              ) : null}
              {ai?.rationale ? (
                <div className="flex flex-col gap-1 rounded-lg bg-iris-soft/40 p-3">
                  <p className="text-xs font-medium text-iris-ink">Vì sao AI gắn nhãn như vậy</p>
                  <p className="text-sm text-foreground/85">{ai.rationale}</p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <section className="flex flex-col gap-3">
            <h2 className="font-heading text-lg">Phản hồi tương tự</h2>
            {similar.isPending ? (
              <Skeleton className="h-24 w-full" />
            ) : (similar.data?.length ?? 0) === 0 ? (
              <Empty className="border">
                <EmptyHeader>
                  <EmptyTitle>Chưa có phản hồi tương tự</EmptyTitle>
                  <EmptyDescription>
                    Phân loại phản hồi này trước để hệ thống so sánh được với các phản hồi khác.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <ul className="flex flex-col gap-2">
                {similar.data!
                  .filter((s, i, all) => all.findIndex((o) => o.snippet === s.snippet) === i)
                  .map((s) => (
                  <li key={s.id}>
                    <Link
                      href={`/feedbacks/${s.id}`}
                      className="flex items-start justify-between gap-4 rounded-lg border bg-card p-3 text-sm transition-colors hover:bg-accent/60 focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <span className="line-clamp-2 flex-1">{s.snippet}</span>
                      <Badge variant="secondary">Giống {Math.round(s.score * 100)}%</Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-20">
          <Card size="sm">
            <CardHeader>
              <CardTitle>Nhãn AI</CardTitle>
              <CardDescription>
                {ai ? (ai.analysis_version ? `Phiên bản ${ai.analysis_version}` : "Đã phân loại") : "Chưa phân loại"}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                {ai?.severity ? (
                  <Badge variant={SEVERITY_TONE[ai.severity] ?? "secondary"}>
                    {SEVERITY_LABEL[lang][ai.severity]}
                  </Badge>
                ) : null}
                {ai?.sentiment ? <SentimentIndicator value={ai.sentiment} /> : null}
                {ai?.safety_issue ? <Badge variant="destructive">Có vấn đề an toàn</Badge> : null}
                {!ai ? <Badge variant="warning">Chờ phân loại</Badge> : null}
              </div>
              <Separator />
              <dl className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] gap-x-3 gap-y-2">
                <dt className="text-muted-foreground">Chủ đề</dt>
                <dd className="flex flex-wrap gap-1">
                  {ai?.uncategorized ? <Badge variant="outline">Chưa có chủ đề phù hợp</Badge> : null}
                  {(ai?.topics ?? []).length > 0
                    ? ai!.topics!.map((t) => (
                        <Badge key={t} variant="secondary" title={t}>
                          {labelTopic(t)}
                        </Badge>
                      ))
                    : ai?.uncategorized
                      ? null
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
                <dt className="text-muted-foreground">Độ tin cậy</dt>
                <dd className="font-mono">
                  {ai?.confidence != null ? `${Math.round(ai.confidence * 100)}%` : "—"}
                </dd>
              </dl>
            </CardContent>
          </Card>

          <Card size="sm">
            <CardHeader>
              <CardTitle>Nguồn</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <PropertyList
                entries={[
                  ["Kênh", d.source],
                  ["Ngày", formatDate(d.occurred_at)],
                  ["Mã bản ghi", d.source_record_id],
                  ["Lô nhập", d.import_id ? d.import_id.slice(0, 8) : null],
                ]}
              />
              {Object.keys(d.source_meta).length > 0 ? (
                <>
                  <Separator />
                  <PropertyList entries={Object.entries(d.source_meta)} />
                </>
              ) : null}
            </CardContent>
          </Card>

          {Object.keys(d.data).length > 0 ? (
            <Card size="sm">
              <CardHeader>
                <CardTitle>Dữ liệu sản phẩm</CardTitle>
                <CardDescription>Các cột thêm trong file nhập.</CardDescription>
              </CardHeader>
              <CardContent>
                <PropertyList entries={Object.entries(d.data)} />
              </CardContent>
            </Card>
          ) : null}
        </aside>
      </div>
    </div>
  )
}

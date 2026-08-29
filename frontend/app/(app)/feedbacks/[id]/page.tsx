"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useFeedbackDetail, useSimilarFeedbacks } from "@/hooks/use-feedback-detail";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { SEVERITY_LABEL, SENTIMENT_LABEL } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";

export default function FeedbackDetailPage() {
  const { id } = useParams<{ id: string }>();
  const fb = useFeedbackDetail(id);
  const similar = useSimilarFeedbacks(id);

  if (fb.isPending)
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
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
    );

  const d = fb.data;
  const ai = d.ai_analysis;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/feedbacks">← Danh sách</Link>
        </Button>
      </div>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Phản hồi · {d.source}</CardTitle>
            {ai?.severity ? (
              <Badge
                variant={
                  ai.severity === "critical" || ai.severity === "high"
                    ? "destructive"
                    : "secondary"
                }
              >
                {SEVERITY_LABEL[ai.severity]}
              </Badge>
            ) : null}
            {ai?.sentiment ? (
              <Badge variant="secondary">{SENTIMENT_LABEL[ai.sentiment]}</Badge>
            ) : null}
            {d.pii_detected ? <Badge variant="outline">Phát hiện PII</Badge> : null}
            {!ai ? <Badge variant="outline">Chưa phân tích</Badge> : null}
          </div>
          <CardDescription>
            {formatDate(d.occurred_at)}
            {d.source_record_id ? ` · ${d.source_record_id}` : ""}
            {d.import_id ? ` · import ${d.import_id.slice(0, 8)}…` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {d.feedback_text ?? "(chưa có nội dung đã sanitize)"}
          </p>
          {ai?.rationale ? (
            <p className="text-xs text-muted-foreground">
              AI: {ai.rationale}{" "}
              {ai.analysis_version ? `(${ai.analysis_version})` : ""}
            </p>
          ) : null}
          <Separator />
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="text-muted-foreground">Chủ đề</dt>
            <dd className="flex flex-wrap gap-1">
              {(ai?.topics ?? []).length > 0
                ? ai!.topics!.map((t) => (
                    <Badge key={t} variant="secondary">
                      {t}
                    </Badge>
                  ))
                : "—"}
            </dd>
            <dt className="text-muted-foreground">Confidence</dt>
            <dd>{ai?.confidence != null ? `${Math.round(ai.confidence * 100)}%` : "—"}</dd>
            <dt className="text-muted-foreground">An toàn</dt>
            <dd>{ai?.safety_issue ? "⚠ Có vấn đề an toàn" : "—"}</dd>
          </dl>

          {Object.keys(d.data).length > 0 ? (
            <>
              <Separator />
              <div>
                <h3 className="mb-2 text-sm font-medium">Product data</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm sm:grid-cols-[10rem_1fr]">
                  {Object.entries(d.data).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd>{String(v)}</dd>
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
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm sm:grid-cols-[10rem_1fr]">
                  {Object.entries(d.source_meta).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd>{String(v)}</dd>
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
          <ul className="flex flex-col gap-2">
            {similar.data!.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/feedbacks/${s.id}`}
                  className="flex items-start justify-between gap-4 rounded-lg border p-3 hover:bg-accent"
                >
                  <span className="line-clamp-2 flex-1 text-sm">
                    {s.snippet}
                  </span>
                  <Badge variant="secondary">{Math.round(s.score * 100)}%</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

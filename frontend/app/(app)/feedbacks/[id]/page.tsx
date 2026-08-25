"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useFeedbackDetail, useSimilarFeedbacks } from "@/hooks/use-feedback-detail";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { REVIEW_LABEL, SEVERITY_LABEL } from "@/lib/labels";
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
            {d.severity ? (
              <Badge
                variant={
                  d.severity === "critical" || d.severity === "high"
                    ? "destructive"
                    : "secondary"
                }
              >
                {SEVERITY_LABEL[d.severity]}
              </Badge>
            ) : null}
            <Badge variant="outline">{REVIEW_LABEL[d.review_status]}</Badge>
            {d.pii_detected ? <Badge variant="outline">Phát hiện PII</Badge> : null}
          </div>
          <CardDescription>
            {formatDate(d.created_at)}
            {d.external_ref ? ` · ${d.external_ref}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {d.sanitized_content ?? "(nội dung trống)"}
          </p>
          <Separator />
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="text-muted-foreground">AI issue</dt>
            <dd>{d.ai_issue ?? "—"}</dd>
            <dt className="text-muted-foreground">Sentiment</dt>
            <dd>{d.sentiment ?? "—"}</dd>
            <dt className="text-muted-foreground">Confidence</dt>
            <dd>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : "—"}</dd>
            <dt className="text-muted-foreground">Categories</dt>
            <dd className="flex flex-wrap gap-1">
              {(d.categories ?? []).length > 0
                ? d.categories!.map((c) => (
                    <Badge key={c} variant="secondary">
                      {c}
                    </Badge>
                  ))
                : "—"}
            </dd>
            <dt className="text-muted-foreground">Cần người duyệt</dt>
            <dd>{d.requires_human_review ? "Có" : "Không"}</dd>
          </dl>
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
                    {s.sanitized_content}
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

"use client";
import { useState } from "react";
import Link from "next/link";
import { CircleHelp, Lightbulb } from "lucide-react";
import { toast } from "sonner";
import { useInsights, useRunInsights } from "@/hooks/use-insights";
import type { InsightItem } from "@/lib/types";
import { formatRelative } from "@/lib/format";
import { SEVERITY_LABEL } from "@/lib/labels";
import { ApiError } from "@/lib/api";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";

const DICTIONARY: [string, string][] = [
  [
    "Insight",
    "Kết luận máy rút ra từ một cụm phản hồi, kèm hành động đề xuất cho team",
  ],
  [
    "Bằng chứng",
    "Trích dẫn nguyên văn từ phản hồi thật — đã ẩn danh hoá trước khi lưu",
  ],
];

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
  );
}

/** Replace-all + gọi LLM vài chục giây → nút disable rõ ràng trong lúc sinh. */
function RunControls({ disabled }: { disabled?: boolean }) {
  const run = useRunInsights();
  const [conflict, setConflict] = useState<string | null>(null);

  function start() {
    setConflict(null);
    run.mutate(undefined, {
      onSuccess: (r) =>
        toast.success(
          `${r.insights_generated} insight · ${(r.duration_ms / 1000).toFixed(0)}s`,
          {
            description:
              r.skipped > 0 ? `${r.skipped} cụm bị bỏ qua do lỗi tạo lập` : undefined,
          },
        ),
      onError: (e) => {
        if (e instanceof ApiError && e.status === 409) {
          // đúng chữ server: hướng dẫn chạy clustering trước
          setConflict(e.message);
        } else {
          toast.error(e instanceof Error ? e.message : "Thất bại.");
        }
      },
    });
  }

  return (
    <>
      <Button onClick={start} disabled={disabled || run.isPending}>
        {run.isPending ? <Spinner data-icon="inline-start" /> : null}
        <Lightbulb data-icon="inline-start" />
        {run.isPending ? "Đang sinh (có thể mất khoảng một phút)" : "Sinh insight"}
      </Button>
      {conflict ? (
        <Alert variant="destructive" className="mt-4">
          <AlertTitle>Chưa thể sinh insight</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span>{conflict}</span>
            <Button asChild size="sm" variant="outline">
              <Link href="/clusters">Đến trang cụm chủ đề</Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
    </>
  );
}

/** Badge mức độ của từng bằng chứng (map màu như bảng feedbacks). */
function SeverityBadge({ severity }: { severity: InsightItem["evidence"][number]["severity"] }) {
  if (!severity) return null;
  return (
    <Badge variant={severity === "critical" || severity === "high" ? "destructive" : "secondary"}>
      {SEVERITY_LABEL[severity]}
    </Badge>
  );
}

function InsightCard({ insight }: { insight: InsightItem }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base leading-snug">{insight.title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">{insight.summary}</p>

        {/* Signature element của màn — hành động là thứ PM tìm tới trang này để lấy */}
        <div className="rounded-r-md border-l-2 border-primary bg-muted/50 px-4 py-3">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Hành động đề xuất
          </p>
          <p className="mt-1 text-sm font-medium">{insight.suggested_action}</p>
        </div>

        {insight.evidence.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Bằng chứng ({insight.evidence.length})
            </h4>
            <ul className="mt-2 flex flex-col gap-2">
              {insight.evidence.map((ev) => (
                <li key={ev.feedback_id}>
                  <blockquote className="border-l-2 border-border pl-3 text-sm">
                    <Link
                      href={`/feedbacks/${ev.feedback_id}`}
                      className="line-clamp-3 underline-offset-2 hover:underline"
                    >
                      “{ev.snippet}
                      {ev.snippet.length >= 200 ? "…" : ""}”
                    </Link>
                    <footer className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <SeverityBadge severity={ev.severity} />
                      <span>{formatRelative(ev.created_at)}</span>
                    </footer>
                  </blockquote>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
      {insight.cluster_id ? (
        <CardFooter>
          <Button asChild size="sm" variant="ghost" className="ml-auto">
            <Link href="/clusters">Xem cụm liên quan</Link>
          </Button>
        </CardFooter>
      ) : null}
    </Card>
  );
}

export default function InsightsPage() {
  const insights = useInsights();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-heading text-2xl">Insight</h1>
        <DictionaryPopover />
        {(insights.data?.items.length ?? 0) > 0 ? (
          <div className="ml-auto">
            <RunControls />
          </div>
        ) : null}
      </div>

      {insights.isPending ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      ) : insights.isError ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Không tải được dữ liệu</EmptyTitle>
            <EmptyDescription>{insights.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : insights.data.items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Chưa có insight nào</EmptyTitle>
            <EmptyDescription className="flex flex-col items-center gap-3">
              <span>
                Máy đọc các cụm chủ đề ưu tiên cao rồi rút ra kết luận kèm hành
                động đề xuất và bằng chứng. Cần có phân cụm trước khi sinh
                insight.
              </span>
              <RunControls />
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <div className="flex flex-col gap-4">
          {insights.data.items.map((it) => (
            <InsightCard key={it.id} insight={it} />
          ))}
        </div>
      )}
    </div>
  );
}

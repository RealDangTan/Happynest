"use client";
import { CircleHelp } from "lucide-react";
import { useInsights } from "@/hooks/use-insights";
import type { InsightItem } from "@/lib/types";
import { formatRelative } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
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

const DICTIONARY: [string, string][] = [
  [
    "Insight",
    "Kết luận có bằng chứng mà agent điều tra rút ra — tách finding (sự thật có dữ liệu) khỏi hypothesis (suy luận)",
  ],
  [
    "Bằng chứng",
    "Kết quả tool phân tích được ghi lại từng bước — insight phải truy ngược được về bằng chứng",
  ],
];

const STATUS_LABEL: Record<InsightItem["status"], string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  edited: "Đã sửa",
  rejected: "Đã loại",
  investigating: "Đang điều tra thêm",
};

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

function InsightCard({ insight }: { insight: InsightItem }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-base leading-snug">
            {insight.title}
          </CardTitle>
          <Badge variant={insight.status === "pending" ? "secondary" : "outline"}>
            {STATUS_LABEL[insight.status]}
          </Badge>
          <Badge variant="outline">
            tin cậy {Math.round(insight.finding_confidence * 100)}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm">{insight.finding}</p>

        {insight.hypothesis?.statement ? (
          <div className="rounded-r-md border-l-2 border-primary bg-muted/50 px-4 py-3">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Giả thuyết (suy luận — chưa xác nhận)
            </p>
            <p className="mt-1 text-sm font-medium">
              {insight.hypothesis.statement}
              {insight.hypothesis.confidence != null
                ? ` · tin cậy ${Math.round(insight.hypothesis.confidence * 100)}%`
                : ""}
            </p>
          </div>
        ) : null}

        {insight.limitations.length > 0 ? (
          <p className="text-xs text-muted-foreground">
            Hạn chế dữ liệu: {insight.limitations.join("; ")}
          </p>
        ) : null}

        {insight.evidence.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Bằng chứng ({insight.evidence.length})
            </h4>
            <ul className="mt-2 flex flex-col gap-2">
              {insight.evidence.map((ev) => (
                <li key={ev.evidence_id}>
                  <blockquote className="border-l-2 border-border pl-3 text-sm">
                    {ev.statement}
                    <footer className="mt-1 text-xs text-muted-foreground">
                      nguồn: {ev.source_tool}
                    </footer>
                  </blockquote>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
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
            <EmptyDescription>
              Agent UNDERSTAND điều tra theo câu hỏi hoặc signal rồi đề xuất
              insight có bằng chứng — bạn duyệt ở Gate #2 (sắp đến trong FE
              Understand).
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

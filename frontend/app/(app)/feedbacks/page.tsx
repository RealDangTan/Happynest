"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Settings2 } from "lucide-react";
import { useFeedbacks, FEEDBACKS_PAGE_SIZE } from "@/hooks/use-feedbacks";
import type { Feedback } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { SENTIMENT_LABEL, SEVERITY_LABEL } from "@/lib/labels";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { DataEntryDialog } from "./data-entry-dialog";

// Cột bật/tắt được. Cột "Nội dung" cố định luôn hiển thị.
type ColumnKey =
  | "source"
  | "occurred"
  | "severity"
  | "sentiment"
  | "topics"
  | "confidence"
  | "pii";

const ALL_COLUMNS: { key: ColumnKey; label: string }[] = [
  { key: "source", label: "Nguồn" },
  { key: "occurred", label: "Thời điểm" },
  { key: "severity", label: "Mức độ" },
  { key: "sentiment", label: "Cảm xúc" },
  { key: "topics", label: "Chủ đề" },
  { key: "confidence", label: "Confidence" },
  { key: "pii", label: "PII" },
];
const DEFAULT_COLUMNS: ColumnKey[] = ["source", "occurred", "severity", "topics"];
const STORAGE_KEY = "feedbacks.columns";

function readStoredColumns(): ColumnKey[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_COLUMNS;
    const parsed = JSON.parse(raw) as string[];
    const valid = parsed.filter((k) =>
      ALL_COLUMNS.some((c) => c.key === k),
    ) as ColumnKey[];
    return valid.length > 0 ? valid : DEFAULT_COLUMNS;
  } catch {
    return DEFAULT_COLUMNS;
  }
}

function ColumnVisibilityMenu({
  visible,
  onToggle,
}: {
  visible: ColumnKey[];
  onToggle: (key: ColumnKey) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings2 data-icon="inline-start" />
          Hiện thị cột
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Cột hiển thị</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_COLUMNS.map(({ key, label }) => (
          <DropdownMenuCheckboxItem
            key={key}
            checked={visible.includes(key)}
            onCheckedChange={() => onToggle(key)}
            onSelect={(e) => e.preventDefault()}
          >
            {label}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function FeedbackCell({ fb }: { fb: Feedback }) {
  return (
    <TableCell className="max-w-md">
      <Link href={`/feedbacks/${fb.id}`} className="block">
        <span className="line-clamp-2">{fb.feedback_text ?? "(chưa phân tích)"}</span>
      </Link>
    </TableCell>
  );
}

function FeedbacksTable() {
  const router = useRouter();
  const sp = useSearchParams();
  const page = Math.max(1, Number(sp.get("page") ?? "1") || 1);
  const filters = {
    page,
    severity: sp.get("severity") ?? undefined,
    sentiment: sp.get("sentiment") ?? undefined,
    topic: sp.get("topic") ?? undefined,
    source: sp.get("source") ?? undefined,
  };
  const { data, isPending, isError, error } = useFeedbacks(filters);

  // localStorage chỉ đọc sau mount — tránh lệch hydration SSR.
  const [visibleColumns, setVisibleColumns] =
    useState<ColumnKey[]>(DEFAULT_COLUMNS);
  useEffect(() => {
    setVisibleColumns(readStoredColumns());
  }, []);

  function toggleColumn(key: ColumnKey) {
    setVisibleColumns((prev) => {
      const next = prev.includes(key)
        ? prev.filter((k) => k !== key)
        : [...prev, key];
      if (next.length === 0) return prev; // không cho ẩn hết mọi cột phụ
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // storage bị chặn (private mode…) → vẫn đổi tạm trong phiên
      }
      return next;
    });
  }

  const has = (key: ColumnKey) => visibleColumns.includes(key);

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(sp.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page"); // đổi lọc → về trang 1
    router.replace(`/feedbacks?${next.toString()}`);
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / FEEDBACKS_PAGE_SIZE));

  if (isPending)
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  if (isError)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Không tải được dữ liệu</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );

  return (
    <div className="flex flex-col gap-4">
      {/* Bộ lọc + tuỳ biến cột */}
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={sp.get("severity") ?? "all"}
          onValueChange={(v) => setParam("severity", v === "all" ? null : v)}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Mức độ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Mọi mức độ</SelectItem>
            {Object.entries(SEVERITY_LABEL).map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={sp.get("sentiment") ?? "all"}
          onValueChange={(v) => setParam("sentiment", v === "all" ? null : v)}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Cảm xúc" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Mọi cảm xúc</SelectItem>
            {Object.entries(SENTIMENT_LABEL).map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Lọc theo chủ đề (topic)…"
          className="w-48"
          defaultValue={sp.get("topic") ?? ""}
          onBlur={(e) => setParam("topic", e.target.value.trim() || null)}
        />
        <Input
          placeholder="Lọc theo nguồn…"
          className="w-44"
          defaultValue={sp.get("source") ?? ""}
          onBlur={(e) => setParam("source", e.target.value.trim() || null)}
        />
        <div className="ml-auto">
          <ColumnVisibilityMenu visible={visibleColumns} onToggle={toggleColumn} />
        </div>
      </div>

      {data.items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Chưa có phản hồi nào</EmptyTitle>
            <EmptyDescription>
              Nhập dữ liệu bằng nút bên trên (thủ công hoặc import CSV qua
              LISTEN) hoặc bỏ bộ lọc.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[45%]">Nội dung</TableHead>
                {has("source") && <TableHead>Nguồn</TableHead>}
                {has("occurred") && <TableHead>Thời điểm</TableHead>}
                {has("severity") && <TableHead>Mức độ</TableHead>}
                {has("sentiment") && <TableHead>Cảm xúc</TableHead>}
                {has("topics") && <TableHead>Chủ đề</TableHead>}
                {has("confidence") && <TableHead>Confidence</TableHead>}
                {has("pii") && <TableHead>PII</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((fb: Feedback) => {
                const ai = fb.ai_analysis;
                return (
                  <TableRow key={fb.id} className="cursor-pointer">
                    <FeedbackCell fb={fb} />
                    {has("source") && <TableCell>{fb.source}</TableCell>}
                    {has("occurred") && (
                      <TableCell className="whitespace-nowrap">
                        {formatDate(fb.occurred_at)}
                      </TableCell>
                    )}
                    {has("severity") && (
                      <TableCell>
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
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    )}
                    {has("sentiment") && (
                      <TableCell>
                        {ai?.sentiment ? (
                          <Badge variant="secondary">
                            {SENTIMENT_LABEL[ai.sentiment]}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    )}
                    {has("topics") && (
                      <TableCell className="max-w-48">
                        {ai?.topics?.length ? (
                          <div className="flex flex-wrap gap-1">
                            {ai.topics.slice(0, 3).map((t) => (
                              <Badge key={t} variant="outline">
                                {t}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    )}
                    {has("confidence") && (
                      <TableCell className="whitespace-nowrap">
                        {ai?.confidence != null
                          ? `${Math.round(ai.confidence * 100)}%`
                          : (
                            <span className="text-muted-foreground">—</span>
                          )}
                      </TableCell>
                    )}
                    {has("pii") && (
                      <TableCell>
                        {fb.pii_detected ? (
                          <Badge variant="outline">PII</Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {total} phản hồi · trang {page}/{totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setParam("page", String(page - 1))}
              >
                Trước
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setParam("page", String(page + 1))}
              >
                Sau
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function FeedbacksPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl">Phản hồi</h1>
        <DataEntryDialog />
      </div>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <FeedbacksTable />
      </Suspense>
    </div>
  );
}

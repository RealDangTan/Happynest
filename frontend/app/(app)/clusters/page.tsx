"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CircleHelp,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import {
  useClusters,
  useRunClustering,
  type ClusterSort,
} from "@/hooks/use-clusters";
import type { ClusterItem } from "@/lib/types";
import { formatRelative } from "@/lib/format";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";

const SORT_OPTIONS: { value: ClusterSort; label: string }[] = [
  { value: "feedback_count", label: "Nhiều phản hồi nhất" },
  { value: "growth_ratio", label: "Tăng nhanh nhất" },
  { value: "recent", label: "Mới nhất" },
];

const DICTIONARY: [string, string][] = [
  ["Cluster (cụm)", "Nhóm phản hồi nói về cùng một vấn đề, máy tự gộp theo ý nghĩa"],
  ["Mới nổi (emerging)", "Vấn đề hoàn toàn mới — kỳ trước chưa ai nhắc, kỳ này xuất hiện đủ nhiều"],
  ["Tăng đột biến (spike)", "Vấn đề đã có nhưng kỳ này tăng vọt so với kỳ trước"],
  ["Tỷ lệ tăng", "So số phản hồi kỳ này với kỳ trước: 2.0× = gấp đôi; <1× = đang lắng"],
  ["Ưu tiên đề xuất", "Điểm 0–1 từ độ phổ biến + tăng trưởng + độ nghiêm trọng — chỉ là gợi ý, người quyết"],
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

/** Map gợi ý 0–1 → nhãn; ngưỡng thuần UI (spec UF-05). */
function priorityLabel(p: number): string {
  if (p >= 0.66) return "cao";
  if (p >= 0.33) return "trung bình";
  return "thấp";
}

/** Cạm bẫy sentinel 9.99: emerging hiển thị chữ "Mới", không hiện số. */
function GrowthCell({ c }: { c: ClusterItem }) {
  if (c.is_emerging) return <Badge variant="default">Mới</Badge>;
  const ratio = c.growth_ratio >= 10 ? null : `${c.growth_ratio.toFixed(1)}×`;
  return (
    <span title={`${c.current_count} so với ${c.previous_count} kỳ trước`}>
      {ratio ?? "—"}
    </span>
  );
}

function ClusterCard({ c }: { c: ClusterItem }) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-snug">{c.name}</CardTitle>
          <div className="flex shrink-0 gap-1">
            {c.is_emerging ? <Badge variant="default">Mới nổi</Badge> : null}
            {c.is_spike ? (
              <Badge variant="destructive">Tăng đột biến</Badge>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <p className="line-clamp-2 text-sm text-muted-foreground">{c.summary}</p>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Tổng phản hồi</dt>
          <dd className="font-medium">{c.feedback_count}</dd>
          <dt className="text-muted-foreground">Kỳ này / kỳ trước</dt>
          <dd>
            {c.current_count} / {c.previous_count}
          </dd>
          <dt className="text-muted-foreground">Tỷ lệ tăng</dt>
          <dd>
            <GrowthCell c={c} />
          </dd>
          {c.suggested_priority != null ? (
            <>
              <dt className="text-muted-foreground">Ưu tiên đề xuất</dt>
              <dd>
                <Badge
                  variant={
                    c.suggested_priority >= 0.66 ? "destructive" : "secondary"
                  }
                >
                  {priorityLabel(c.suggested_priority)}
                </Badge>
              </dd>
            </>
          ) : null}
        </dl>
      </CardContent>
      <CardFooter className="flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="flex flex-wrap gap-x-2">
          {c.sample_feedback_ids.slice(0, 5).map((id, i) => (
            <span key={id}>
              {i > 0 ? "· " : ""}
              <Link
                href={`/feedbacks/${id}`}
                className="underline underline-offset-2 hover:text-foreground"
              >
                mẫu {i + 1}
              </Link>
            </span>
          ))}
        </span>
        <span>{formatRelative(c.last_seen)}</span>
      </CardFooter>
    </Card>
  );
}

function RebuildButton({ disabled }: { disabled?: boolean }) {
  const run = useRunClustering();
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" disabled={disabled || run.isPending}>
          {run.isPending ? <Spinner data-icon="inline-start" /> : null}
          <RefreshCw data-icon="inline-start" />
          Tạo lại phân cụm
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Tạo lại toàn bộ phân cụm?</AlertDialogTitle>
          <AlertDialogDescription>
            Thao tác XOÁ TOÀN BỘ insights và clusters hiện có rồi phân lại từ
            đầu trên mọi phản hồi đã có embedding. Không thể hoàn tác.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Huỷ</AlertDialogCancel>
          <AlertDialogAction
            onClick={() =>
              run.mutate(undefined, {
                onSuccess: (r) =>
                  toast.success("Phân cụm hoàn tất", {
                    description: `${r.clusters_upserted} cụm · ${r.assigned_count} phản hồi được gán · ${r.unassigned_count} chưa gán (nhiễu/chưa embed) · ${(r.duration_ms / 1000).toFixed(1)}s`,
                  }),
                onError: (e) =>
                  toast.error(e instanceof Error ? e.message : "Thất bại."),
              })
            }
          >
            Xác nhận tạo lại
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function ClustersInner() {
  const router = useRouter();
  const sp = useSearchParams();
  const rawSort = sp.get("sort");
  const sort: ClusterSort = SORT_OPTIONS.some((o) => o.value === rawSort)
    ? (rawSort as ClusterSort)
    : "feedback_count";
  const clusters = useClusters(sort);

  function setSort(v: string) {
    const next = new URLSearchParams(sp.toString());
    next.set("sort", v);
    router.replace(`/clusters?${next.toString()}`);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-heading text-2xl">Cụm chủ đề</h1>
        <DictionaryPopover />
        <div className="ml-auto flex items-center gap-2">
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger className="w-52">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(clusters.data?.items.length ?? 0) > 0 ? <RebuildButton /> : null}
        </div>
      </div>

      {clusters.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56 w-full" />
          ))}
        </div>
      ) : clusters.isError ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Không tải được dữ liệu</EmptyTitle>
            <EmptyDescription>{clusters.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : clusters.data.items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Chưa có phân cụm nào</EmptyTitle>
            <EmptyDescription className="flex flex-col items-center gap-3">
              <span>
                Chạy phân cụm để gộp các phản hồi đã phân loại thành nhóm chủ
                đề — kèm phát hiện vấn đề mới nổi và tăng đột biến.
              </span>
              <RebuildButton />
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="size-4" />
            {clusters.data.items.length} cụm · sắp theo{" "}
            {SORT_OPTIONS.find((o) => o.value === sort)?.label.toLowerCase()}
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {clusters.data.items.map((c) => (
              <ClusterCard key={c.id} c={c} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function ClustersPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <ClustersInner />
    </Suspense>
  );
}

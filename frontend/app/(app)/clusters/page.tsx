"use client"
import { Suspense } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { CircleHelp, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import {
  useClusters,
  useRunClustering,
  type ClusterSort,
} from "@/hooks/use-clusters"
import type { ClusterItem } from "@/lib/types"
import { useFeedbackDetail } from "@/hooks/use-feedback-detail"
import { cn } from "@/lib/utils"
import { formatRelative } from "@/lib/format"
import { priorityLabel } from "@/lib/labels"
import { useAppLang } from "@/lib/i18n"
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
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { PageHeader } from "@/components/page-header"

const SORT_OPTIONS: { value: ClusterSort; label: string }[] = [
  { value: "feedback_count", label: "Nhiều phản hồi nhất" },
  { value: "growth_ratio", label: "Tăng nhanh nhất" },
  { value: "recent", label: "Mới nhất" },
]

const DICTIONARY: [string, string][] = [
  [
    "Cluster (cụm)",
    "Nhóm phản hồi nói về cùng một vấn đề, máy tự gộp theo ý nghĩa",
  ],
  [
    "Mới nổi (emerging)",
    "Vấn đề hoàn toàn mới — kỳ trước chưa ai nhắc, kỳ này xuất hiện đủ nhiều",
  ],
  [
    "Tăng đột biến (spike)",
    "Vấn đề đã có nhưng kỳ này tăng vọt so với kỳ trước",
  ],
  [
    "Tỷ lệ tăng",
    "So số phản hồi kỳ này với kỳ trước: 2.0× = gấp đôi; <1× = đang lắng",
  ],
  [
    "Ưu tiên đề xuất",
    "Điểm 0–1 từ độ phổ biến + tăng trưởng + độ nghiêm trọng — chỉ là gợi ý, người quyết",
  ],
]

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

/** Cạm bẫy sentinel 9.99: emerging hiển thị chữ "Mới", không hiện số. */
function GrowthCell({ c }: { c: ClusterItem }) {
  if (c.is_emerging) return <Badge variant="default">Mới</Badge>
  // Kỳ trước 0 thì không có cơ sở so sánh — "0.0×" sẽ đọc như đang lắng.
  const ratio =
    c.previous_count === 0 || c.growth_ratio >= 10 ? null : `${c.growth_ratio.toFixed(1)}×`
  return (
    <span title={`${c.current_count} so với ${c.previous_count} kỳ trước`}>
      {ratio ?? "—"}
    </span>
  )
}

/** Kỳ trước → kỳ này dưới dạng hai thanh, đọc được xu hướng mà không cần số. */
function PeriodBars({ c, max }: { c: ClusterItem; max: number }) {
  // 0 phản hồi = không vẽ thanh, để không đọc nhầm thành "có một ít".
  const pct = (n: number) => (n <= 0 ? "0%" : `${Math.max(3, (n / Math.max(max, 1)) * 100)}%`)
  return (
    <div className="flex flex-col gap-1" aria-label={`Kỳ trước ${c.previous_count}, kỳ này ${c.current_count}`}>
      <span className="flex items-center gap-2">
        <span className="w-14 shrink-0 text-[11px] text-muted-foreground">Kỳ trước</span>
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <span className="block h-full rounded-full bg-muted-foreground/40" style={{ width: pct(c.previous_count) }} />
        </span>
        <span className="w-8 text-right font-mono text-[11px] text-muted-foreground">{c.previous_count}</span>
      </span>
      <span className="flex items-center gap-2">
        <span className="w-14 shrink-0 text-[11px] text-muted-foreground">Kỳ này</span>
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <span
            className={cn("block h-full rounded-full", c.is_spike || c.is_emerging ? "bg-coral" : "bg-sky")}
            style={{ width: pct(c.current_count) }}
          />
        </span>
        <span className="w-8 text-right font-mono text-[11px]">{c.current_count}</span>
      </span>
    </div>
  )
}

function ClusterRow({
  c,
  max,
  active,
  onSelect,
}: {
  c: ClusterItem
  max: number
  active: boolean
  onSelect: () => void
}) {
  return (
    <li>
      <button
        type="button"
        aria-current={active ? "true" : undefined}
        onClick={onSelect}
        className={cn(
          "flex w-full flex-col gap-2 rounded-lg border-l-2 px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-ring",
          active ? "border-l-signal bg-accent" : "border-l-transparent hover:bg-accent/50"
        )}
      >
        <span className="flex flex-wrap items-center gap-2">
          <span className="min-w-0 flex-1 font-heading text-sm leading-snug">{c.name}</span>
          {c.is_emerging ? <Badge variant="default">Mới nổi</Badge> : null}
          {c.is_spike ? <Badge variant="destructive">Tăng đột biến</Badge> : null}
          <span className="font-mono text-xs text-muted-foreground">{c.feedback_count}</span>
        </span>
        <PeriodBars c={c} max={max} />
      </button>
    </li>
  )
}

function SampleFeedback({ id }: { id: string }) {
  const fb = useFeedbackDetail(id)
  return (
    <li>
      <Link
        href={`/feedbacks/${id}`}
        className="flex flex-col gap-1 rounded-lg border bg-card p-2.5 text-sm transition-colors hover:bg-accent/60 focus-visible:outline-2 focus-visible:outline-ring"
      >
        {fb.isPending ? (
          <Skeleton className="h-10 w-full" />
        ) : (
          <span className="line-clamp-3 leading-relaxed">
            “{fb.data?.feedback_text ?? "Chưa đọc được phản hồi này."}”
          </span>
        )}
        <span className="font-mono text-[11px] text-muted-foreground">F-{id.slice(0, 8)}</span>
      </Link>
    </li>
  )
}

/** Panel cụm đang chọn (mẫu Dovetail Themes): xu hướng + phản hồi mẫu cùng màn. */
function ClusterPanel({ c, max }: { c: ClusterItem; max: number }) {
  const lang = useAppLang()
  return (
    <Card size="sm" className="self-start lg:sticky lg:top-20">
      <CardHeader>
        <p className="text-xs text-muted-foreground">Cụm đang xem · cập nhật {formatRelative(c.last_seen)}</p>
        <CardTitle className="font-heading text-lg leading-snug">{c.name}</CardTitle>
        <CardAction className="flex gap-1">
          {c.is_emerging ? <Badge variant="default">Mới nổi</Badge> : null}
          {c.is_spike ? <Badge variant="destructive">Tăng đột biến</Badge> : null}
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {c.summary ? <p className="text-sm leading-relaxed text-foreground/85">{c.summary}</p> : null}
        <dl className="grid grid-cols-3 gap-3 text-sm">
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">Tổng phản hồi</dt>
            <dd className="font-mono text-base">{c.feedback_count}</dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">Tỷ lệ tăng</dt>
            <dd className="font-mono text-base"><GrowthCell c={c} /></dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">Ưu tiên</dt>
            <dd>
              {c.suggested_priority != null ? (
                <Badge variant={c.suggested_priority >= 0.66 ? "destructive" : "secondary"}>
                  {priorityLabel(c.suggested_priority, lang)}
                </Badge>
              ) : (
                "—"
              )}
            </dd>
          </div>
        </dl>
        <PeriodBars c={c} max={max} />
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Phản hồi mẫu ({Math.min(5, c.sample_feedback_ids.length)})
          </h3>
          {c.sample_feedback_ids.length ? (
            <ul className="flex flex-col gap-2">
              {c.sample_feedback_ids.slice(0, 5).map((id) => (
                <SampleFeedback key={id} id={id} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Cụm này chưa có phản hồi mẫu.</p>
          )}
        </section>
      </CardContent>
      <CardFooter>
        <Button size="sm" variant="outline" asChild>
          <Link href="/data-graph?ask=1">Hỏi AI về vấn đề này</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

function RebuildButton({ disabled }: { disabled?: boolean }) {
  const run = useRunClustering()
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
  )
}

function ClustersInner() {
  const router = useRouter()
  const sp = useSearchParams()
  const rawSort = sp.get("sort")
  const sort: ClusterSort = SORT_OPTIONS.some((o) => o.value === rawSort)
    ? (rawSort as ClusterSort)
    : "feedback_count"
  const clusters = useClusters(sort)

  function setSort(v: string) {
    const next = new URLSearchParams(sp.toString())
    next.set("sort", v)
    router.replace(`/clusters?${next.toString()}`)
  }
  // ?cluster= giữ cụm đang mở qua refresh/back; mặc định là cụm đầu danh sách.
  const items = clusters.data?.items ?? []
  const selected = items.find((c) => c.id === sp.get("cluster")) ?? items[0] ?? null
  const maxCount = Math.max(1, ...items.flatMap((c) => [c.current_count, c.previous_count]))
  function selectCluster(id: string) {
    const next = new URLSearchParams(sp.toString())
    next.set("cluster", id)
    router.replace(`/clusters?${next.toString()}`, { scroll: false })
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Cụm chủ đề"
        description="Các phản hồi được gộp theo ý nghĩa — kèm phát hiện vấn đề mới nổi và tăng đột biến."
        actions={
          <>
            <DictionaryPopover />
            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="w-52" aria-label="Sắp xếp cụm">
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
          </>
        }
      />

      {clusters.isPending ? (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,26rem)]">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
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
                Chạy phân cụm để gộp các phản hồi đã phân loại thành nhóm chủ đề
                — kèm phát hiện vấn đề mới nổi và tăng đột biến.
              </span>
              <RebuildButton />
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,26rem)]">
          <Card size="sm" className="min-w-0">
            <CardHeader>
              <CardTitle>{clusters.data.items.length} cụm</CardTitle>
              <CardAction>
                <span className="text-xs text-muted-foreground">
                  Sắp theo {SORT_OPTIONS.find((o) => o.value === sort)?.label.toLowerCase()}
                </span>
              </CardAction>
            </CardHeader>
            <CardContent>
              {/* Danh sách cuộn trong khung để panel cụm đang chọn luôn nằm
                  cạnh, kể cả khi có vài chục cụm. */}
              <ul className="-mx-1 flex max-h-[calc(100dvh-14rem)] flex-col gap-1 overflow-y-auto px-1">

                {clusters.data.items.map((c) => (
                  <ClusterRow
                    key={c.id}
                    c={c}
                    max={maxCount}
                    active={selected?.id === c.id}
                    onSelect={() => selectCluster(c.id)}
                  />
                ))}
              </ul>
            </CardContent>
          </Card>
          {selected ? <ClusterPanel key={selected.id} c={selected} max={maxCount} /> : null}
        </div>
      )}
    </div>
  )
}

export default function ClustersPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <ClustersInner />
    </Suspense>
  )
}

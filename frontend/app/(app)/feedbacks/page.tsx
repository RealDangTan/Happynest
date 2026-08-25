"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useFeedbacks, FEEDBACKS_PAGE_SIZE } from "@/hooks/use-feedbacks";
import type { Feedback } from "@/lib/types";
import { formatDate } from "@/lib/format";
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

const SEVERITY_LABEL: Record<string, string> = {
  low: "Thấp",
  medium: "Trung bình",
  high: "Cao",
  critical: "Nghiêm trọng",
};
const REVIEW_LABEL: Record<string, string> = {
  unreviewed: "Chưa duyệt",
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  edited: "Đã sửa",
  rejected: "Đã loại",
};

function FeedbacksTable() {
  const router = useRouter();
  const sp = useSearchParams();
  const page = Math.max(1, Number(sp.get("page") ?? "1") || 1);
  const filters = {
    page,
    reviewStatus: sp.get("review_status") ?? undefined,
    severity: sp.get("severity") ?? undefined,
    category: sp.get("category") ?? undefined,
  };
  const { data, isPending, isError, error } = useFeedbacks(filters);

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
      {/* Bộ lọc */}
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={sp.get("severity") ?? "all"}
          onValueChange={(v) => setParam("severity", v === "all" ? null : v)}
        >
          <SelectTrigger className="w-44">
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
          value={sp.get("review_status") ?? "all"}
          onValueChange={(v) => setParam("review_status", v === "all" ? null : v)}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Trạng thái" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Mọi trạng thái</SelectItem>
            {Object.entries(REVIEW_LABEL).map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Lọc theo category…"
          className="w-52"
          defaultValue={sp.get("category") ?? ""}
          onBlur={(e) => setParam("category", e.target.value.trim() || null)}
        />
      </div>

      {data.items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Chưa có phản hồi nào</EmptyTitle>
            <EmptyDescription>
              Nhập dữ liệu bằng nút bên trên hoặc bỏ bộ lọc.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[45%]">Nội dung</TableHead>
                <TableHead>Nguồn</TableHead>
                <TableHead>Ngày tạo</TableHead>
                <TableHead>Mức độ</TableHead>
                <TableHead>Duyệt</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((fb: Feedback) => (
                <TableRow key={fb.id} className="cursor-pointer">
                  <TableCell className="max-w-md">
                    <Link href={`/feedbacks/${fb.id}`} className="block">
                      <span className="line-clamp-2">
                        {fb.sanitized_content ?? "(trống)"}
                      </span>
                      {fb.pii_detected ? (
                        <Badge variant="outline" className="mt-1">
                          PII
                        </Badge>
                      ) : null}
                    </Link>
                  </TableCell>
                  <TableCell>{fb.source}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(fb.created_at)}
                  </TableCell>
                  <TableCell>
                    {fb.severity ? (
                      <Badge
                        variant={
                          fb.severity === "critical" || fb.severity === "high"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {SEVERITY_LABEL[fb.severity]}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{REVIEW_LABEL[fb.review_status]}</Badge>
                  </TableCell>
                </TableRow>
              ))}
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
      <h1 className="font-heading text-2xl">Phản hồi</h1>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <FeedbacksTable />
      </Suspense>
    </div>
  );
}

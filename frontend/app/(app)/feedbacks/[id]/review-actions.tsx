"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import {
  useFeedbackRaw,
  usePendingNeighbors,
  useSubmitReview,
} from "@/hooks/use-review";
import { ApiError } from "@/lib/api";
import type { Feedback } from "@/lib/types";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

/**
 * Thanh hành động HITL — CHỈ render khi review_status === "pending".
 * Chứa NGOẠI LỆ DUY NHẤT của app gọi include_raw=true (useFeedbackRaw);
 * toggle mặc định TẮT mỗi lần mount (UF-04 Màn 2, decisions 2026-08-26).
 */
export function ReviewActions({ d }: { d: Feedback }) {
  const router = useRouter();
  const qc = useQueryClient();
  const review = useSubmitReview(d.id);
  const nextPending = usePendingNeighbors(d.id);

  // Raw gốc chưa che PII — chỉ query khi reviewer bật toggle.
  const [showRaw, setShowRaw] = useState(false);
  const raw = useFeedbackRaw(d.id, showRaw);

  const [editOpen, setEditOpen] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [editReason, setEditReason] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // 409 = mục đã được người/tab khác xử lý → refresh trạng thái thật.
  function handleError(err: unknown) {
    if (
      err instanceof ApiError &&
      (err.status === 409 || err.status === 503)
    ) {
      void qc.invalidateQueries({ queryKey: ["feedback", d.id] });
      if (err.status === 409) {
        toast.info("Mục này đã được xử lý trước đó.");
        return;
      }
    }
    toast.error(err instanceof Error ? err.message : "Thao tác thất bại.");
  }

  function goNext(nextId: string | null) {
    if (!nextId) return;
    toast.success("Đã ghi nhận.", {
      action: {
        label: "Xem mục tiếp theo",
        onClick: () => router.push(`/feedbacks/${nextId}`),
      },
    });
  }

  function openEdit() {
    // Prefill LUÔN là bản sanitized — không tự điền raw vào textarea.
    setEditedContent(d.sanitized_content ?? "");
    setEditReason("");
    setEditOpen(true);
  }

  function submitApprove() {
    review.mutate(
      { action: "approve" },
      {
        onSuccess: () => goNext(nextPending.data ?? null),
        onError: handleError,
      },
    );
  }

  function submitEdit() {
    if (!editedContent.trim()) return;
    review.mutate(
      {
        action: "edit",
        edited_content: editedContent,
        reason: editReason.trim() || undefined,
      },
      {
        onSuccess: () => {
          setEditOpen(false);
          toast.success("Đã lưu nội dung chỉnh sửa.");
          goNext(nextPending.data ?? null);
        },
        onError: handleError,
      },
    );
  }

  function submitReject() {
    review.mutate(
      { action: "reject", reason: rejectReason.trim() || undefined },
      {
        onSuccess: () => {
          setRejectOpen(false);
          toast.success("Đã từ chối mục này.");
          goNext(nextPending.data ?? null);
        },
        onError: handleError,
      },
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/40 p-3">
        <ShieldCheck
          className="text-muted-foreground"
          data-icon="inline-start"
        />
        <span className="text-sm font-medium">Hàng chờ duyệt</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            disabled={review.isPending}
            onClick={submitApprove}
          >
            {review.isPending && !editOpen && !rejectOpen ? (
              <Spinner data-icon="inline-start" />
            ) : null}
            Duyệt
          </Button>
          <Button size="sm" variant="outline" disabled={review.isPending} onClick={openEdit}>
            Sửa nội dung
          </Button>
          <AlertDialog open={rejectOpen} onOpenChange={setRejectOpen}>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline" disabled={review.isPending}>
                Từ chối
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Từ chối phản hồi này?</AlertDialogTitle>
                <AlertDialogDescription>
                  Mục sẽ bị đánh dấu rejected và KHÔNG tham gia phân tích. Thao
                  tác không hoàn tác.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <Field>
                <FieldLabel htmlFor="reject-reason">Lý do (khuyến khích)</FieldLabel>
                <Textarea
                  id="reject-reason"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Vì sao loại mục này"
                />
              </Field>
              <AlertDialogFooter>
                <AlertDialogCancel>Huỷ</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-white hover:bg-destructive/90"
                  disabled={review.isPending}
                  onClick={(e) => {
                    e.preventDefault();
                    submitReject();
                  }}
                >
                  {review.isPending && rejectOpen ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  Xác nhận từ chối
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Toggle bản gốc — ngoại lệ PII duy nhất, mặc định tắt mỗi lần mở trang. */}
      <div className="flex items-center gap-2 text-sm">
        <Switch
          id={`raw-${d.id}`}
          checked={showRaw}
          onCheckedChange={setShowRaw}
          aria-label="Hiện bản gốc"
        />
        <label htmlFor={`raw-${d.id}`} className="flex items-center gap-1 cursor-pointer">
          <Eye className="size-4 text-muted-foreground" />
          Hiện bản gốc
        </label>
        <span className="text-xs text-muted-foreground">
          (chỉ để đối chiếu sanitizer; tắt trước khi share màn hình)
        </span>
      </div>

      {showRaw ? (
        <Alert variant="destructive">
          <AlertTitle>Đang hiển thị dữ liệu gốc chưa che PII</AlertTitle>
          <AlertDescription>
            Tắt toggle này trước khi share màn hình.
          </AlertDescription>
        </Alert>
      ) : null}
      {showRaw ? (
        raw.isPending ? (
          <p className="text-sm text-muted-foreground">Đang tải bản gốc…</p>
        ) : raw.isError ? (
          <p className="text-sm text-destructive">Không tải được bản gốc: {raw.error.message}</p>
        ) : (
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border bg-muted/30 p-3 text-sm">
            {raw.data.raw_content}
          </pre>
        )
      ) : null}

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sửa nội dung phản hồi</DialogTitle>
            <DialogDescription>
              Nội dung đã chỉnh sửa chạy lại bộ che PII trước khi lưu. Thao tác
              không hoàn tác.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={!editedContent.trim() ? true : undefined}>
              <FieldLabel htmlFor="edited-content">Nội dung mới</FieldLabel>
              <Textarea
                id="edited-content"
                aria-invalid={!editedContent.trim()}
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                rows={6}
              />
              {!editedContent.trim() ? (
                <FieldDescription>Nội dung không được để trống.</FieldDescription>
              ) : null}
            </Field>
            <Field>
              <FieldLabel htmlFor="edit-reason">Lý do sửa (tuỳ chọn)</FieldLabel>
              <Textarea
                id="edit-reason"
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                placeholder="Vì sao phải sửa"
                rows={2}
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Huỷ
            </Button>
            <Button disabled={!editedContent.trim() || review.isPending} onClick={submitEdit}>
              {review.isPending && editOpen ? <Spinner data-icon="inline-start" /> : null}
              Lưu chỉnh sửa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Separator />
    </div>
  );
}

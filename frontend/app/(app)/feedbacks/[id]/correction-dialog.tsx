"use client";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { PenLine, X } from "lucide-react";
import { toast } from "sonner";
import { useSubmitCorrection } from "@/hooks/use-review";
import { ApiError } from "@/lib/api";
import type { AiIssue, Feedback, Sentiment, Severity } from "@/lib/types";
import {
  AI_ISSUE_LABEL,
  SENTIMENT_LABEL,
  SEVERITY_LABEL,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";

const KEEP = "__keep__";

/** Gợi ý categories gom từ mọi list feedback đã load trong cache. */
function useCategorySuggestions(): string[] {
  const qc = useQueryClient();
  return useMemo(() => {
    const seen = new Set<string>();
    for (const [, data] of qc.getQueriesData<{ items: Feedback[] }>({
      queryKey: ["feedbacks"],
    })) {
      for (const fb of data?.items ?? []) {
        for (const c of fb.categories ?? []) seen.add(c);
      }
    }
    return [...seen].sort();
  }, [qc]);
}

function EnumSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={KEEP}>— giữ nguyên —</SelectItem>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  );
}

/**
 * Sửa NHÃN AI (không đụng nội dung) — áp cho mọi feedback đã classify
 * (categories != null), bất kể review_status. Null = giữ nguyên (OQ-9).
 */
export function CorrectionDialog({ d }: { d: Feedback }) {
  const correction = useSubmitCorrection(d.id);
  const suggestions = useCategorySuggestions();

  const [open, setOpen] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [newCategory, setNewCategory] = useState("");
  const [aiIssue, setAiIssue] = useState(KEEP);
  const [severity, setSeverity] = useState(KEEP);
  const [sentiment, setSentiment] = useState(KEEP);
  const [note, setNote] = useState("");

  function reset() {
    setCategories([]);
    setNewCategory("");
    setAiIssue(KEEP);
    setSeverity(KEEP);
    setSentiment(KEEP);
    setNote("");
  }

  function addCategory() {
    const c = newCategory.trim();
    if (!c || categories.includes(c)) return;
    setCategories((prev) => [...prev, c]);
    setNewCategory("");
  }

  const dirty =
    categories.length > 0 ||
    aiIssue !== KEEP ||
    severity !== KEEP ||
    sentiment !== KEEP;

  function submit() {
    if (!dirty) return;
    correction.mutate(
      {
        ...(categories.length > 0 ? { categories } : {}),
        ...(aiIssue !== KEEP ? { ai_issue: aiIssue as AiIssue } : {}),
        ...(severity !== KEEP ? { severity: severity as Severity } : {}),
        ...(sentiment !== KEEP ? { sentiment: sentiment as Sentiment } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      },
      {
        onSuccess: () => {
          setOpen(false);
          reset();
          toast.success(
            "Đã ghi nhận chỉnh sửa — sẽ giúp phân loại sau chính xác hơn.",
          );
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError && err.status === 409
              ? "Feedback chưa classify — hãy chạy Analysis trước."
              : err instanceof Error
                ? err.message
                : "Ghi nhận chỉnh sửa thất bại.",
          ),
      },
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <PenLine data-icon="inline-start" />
          Sửa nhãn
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sửa nhãn phân loại</DialogTitle>
          <DialogDescription>
            Chỉ nhãn được thay đổi mới gửi đi. Mỗi chỉnh sửa được ghi lại để
            cải thiện phân loại tự động về sau.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="correction-categories">Categories</FieldLabel>
            <div className="flex gap-2">
              <Input
                id="correction-categories"
                value={newCategory}
                placeholder="Thêm category…"
                onChange={(e) => setNewCategory(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCategory();
                  }
                }}
              />
              <Button variant="outline" onClick={addCategory}>
                Thêm
              </Button>
            </div>
            {suggestions.length > 0 ? (
              <FieldDescription>
                Có sẵn:{" "}
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="mr-1 underline underline-offset-2"
                    onClick={() => {
                      if (!categories.includes(s)) {
                        setCategories((prev) => [...prev, s]);
                      }
                    }}
                  >
                    {s}
                  </button>
                ))}
              </FieldDescription>
            ) : null}
            {categories.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {categories.map((c) => (
                  <Badge key={c} variant="secondary">
                    {c}
                    <button
                      type="button"
                      aria-label={`Xóa ${c}`}
                      onClick={() =>
                        setCategories((prev) => prev.filter((x) => x !== c))
                      }
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            ) : (
              <FieldDescription>
                Hiện tại: {(d.categories ?? []).join(", ") || "—"}
              </FieldDescription>
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <EnumSelect
              id="correction-ai-issue"
              label="AI issue"
              value={aiIssue}
              onChange={setAiIssue}
              options={Object.entries(AI_ISSUE_LABEL).map(([value, label]) => ({
                value,
                label,
              }))}
            />
            <EnumSelect
              id="correction-severity"
              label="Mức độ"
              value={severity}
              onChange={setSeverity}
              options={Object.entries(SEVERITY_LABEL).map(([value, label]) => ({
                value,
                label,
              }))}
            />
            <EnumSelect
              id="correction-sentiment"
              label="Cảm xúc"
              value={sentiment}
              onChange={setSentiment}
              options={Object.entries(SENTIMENT_LABEL).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          </div>
          <Field>
            <FieldLabel htmlFor="correction-note">Ghi chú (tuỳ chọn)</FieldLabel>
            <Textarea
              id="correction-note"
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Vì sao sửa nhãn"
            />
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Huỷ
          </Button>
          <Button disabled={!dirty || correction.isPending} onClick={submit}>
            {correction.isPending ? <Spinner data-icon="inline-start" /> : null}
            Lưu nhãn
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

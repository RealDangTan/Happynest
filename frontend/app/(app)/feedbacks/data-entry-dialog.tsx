"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { Feedback } from "@/lib/types";
import { CsvImportWizard } from "./csv-import-wizard";

export function DataEntryDialog() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  function refreshList() {
    void qc.invalidateQueries({ queryKey: ["feedbacks"] });
    router.refresh();
  }

  const createOne = useMutation({
    mutationFn: (body: {
      source: string;
      content: string;
      source_record_id?: string;
      occurred_at?: string;
    }) =>
      apiFetch<Feedback>("/api/feedbacks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("Đã thêm phản hồi.");
      setOpen(false);
      refreshList();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Lỗi không rõ"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Thêm dữ liệu</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Thêm phản hồi</DialogTitle>
          <DialogDescription>
            Nhập từng dòng, hoặc import CSV qua pipeline LISTEN (AI đề xuất
            mapping — bạn duyệt trước khi nạp).
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="manual">
          <TabsList>
            <TabsTrigger value="manual">Thủ công</TabsTrigger>
            <TabsTrigger value="csv">Import CSV (LISTEN)</TabsTrigger>
          </TabsList>

          <TabsContent value="manual">
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const content = String(f.get("content") ?? "").trim();
                const occurred = String(f.get("occurred_at") ?? "").trim();
                if (!content) {
                  toast.error("Nội dung không được rỗng.");
                  return;
                }
                createOne.mutate({
                  source: String(f.get("source") ?? "").trim() || "manual",
                  content,
                  source_record_id:
                    String(f.get("source_record_id") ?? "").trim() || undefined,
                  occurred_at: occurred || undefined,
                });
              }}
            >
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="source">Nguồn</FieldLabel>
                  <Input
                    id="source"
                    name="source"
                    placeholder="app_review, survey, email…"
                    defaultValue="manual"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="source_record_id">
                    ID gốc (tuỳ chọn)
                  </FieldLabel>
                  <Input
                    id="source_record_id"
                    name="source_record_id"
                    placeholder="review#123"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="occurred_at">
                    Thời điểm phản hồi (tuỳ chọn, ISO 8601)
                  </FieldLabel>
                  <Input
                    id="occurred_at"
                    name="occurred_at"
                    placeholder="2026-08-20T10:00:00+07:00"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="content">Nội dung *</FieldLabel>
                  <Textarea id="content" name="content" required rows={4} />
                </Field>
              </FieldGroup>
              <Button type="submit" disabled={createOne.isPending}>
                {createOne.isPending ? <Spinner data-icon="inline-start" /> : null}
                Lưu
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="csv">
            <CsvImportWizard onImported={refreshList} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

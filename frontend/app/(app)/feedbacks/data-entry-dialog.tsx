"use client";
import { useRef, useState } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { Feedback, ImportCsvResult } from "@/lib/types";
import { useCreateSource, useSources } from "@/hooks/use-sources";

const NEW_SOURCE = "__register-new__";

export function DataEntryDialog() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [sourceValue, setSourceValue] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState<1 | 2>(1);
  const [draft, setDraft] = useState<{ name: string; description: string }>({
    name: "",
    description: "",
  });
  const fileRef = useRef<HTMLInputElement>(null);
  const sources = useSources();
  const createSource = useCreateSource();

  function refreshList() {
    void qc.invalidateQueries({ queryKey: ["feedbacks"] });
    router.refresh();
  }

  const activeSources = (sources.data ?? []).filter((s) => s.isActive);

  function openWizard() {
    setDraft({ name: "", description: "" });
    setWizardStep(1);
    setWizardOpen(true);
  }

  const createOne = useMutation({
    mutationFn: (body: { source: string; content: string; external_ref?: string }) =>
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

  const importCsv = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      // KHÔNG set Content-Type tay — trình duyệt tự thêm boundary multipart
      return apiFetch<ImportCsvResult>("/api/feedbacks/import-csv", {
        method: "POST",
        body: fd,
      });
    },
    onSuccess: (r) => {
      toast.success(`Import xong: ${r.imported} dòng mới, ${r.failed} lỗi.`);
      refreshList();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Lỗi không rõ"),
  });

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button>Thêm dữ liệu</Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Thêm phản hồi</DialogTitle>
            <DialogDescription>Nhập từng dòng hoặc import cả file CSV.</DialogDescription>
          </DialogHeader>
          <Tabs defaultValue="manual">
            <TabsList>
              <TabsTrigger value="manual">Thủ công</TabsTrigger>
              <TabsTrigger value="csv">Import CSV</TabsTrigger>
            </TabsList>

            <TabsContent value="manual">
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!sourceValue) {
                    toast.error("Hãy chọn hoặc đăng ký nguồn trước khi lưu.");
                    return;
                  }
                  const f = new FormData(e.currentTarget);
                  createOne.mutate({
                    source: sourceValue,
                    content: String(f.get("content") ?? "").trim(),
                    external_ref: String(f.get("external_ref") ?? "").trim() || undefined,
                  });
                }}
              >
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="source">Nguồn *</FieldLabel>
                    <Select
                      value={sourceValue}
                      onValueChange={(v) =>
                        v === NEW_SOURCE ? openWizard() : setSourceValue(v)
                      }
                    >
                      <SelectTrigger id="source" className="w-full">
                        <SelectValue placeholder="Chọn hoặc đăng ký nguồn…" />
                      </SelectTrigger>
                      <SelectContent>
                        {activeSources.map((s) => (
                          <SelectItem key={s.id} value={s.name}>
                            {s.name}
                          </SelectItem>
                        ))}
                        <SelectItem value={NEW_SOURCE}>
                          ＋ Đăng ký nguồn mới…
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {activeSources.length === 0 && !sources.isPending ? (
                      <p className="text-xs text-muted-foreground">
                        Chưa có nguồn nào — chọn “＋ Đăng ký nguồn mới…” để tạo.
                      </p>
                    ) : null}
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="external_ref">Tham chiếu ngoài (tuỳ chọn)</FieldLabel>
                    <Input id="external_ref" name="external_ref" placeholder="review#123" />
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
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  const file = fileRef.current?.files?.[0];
                  if (file) importCsv.mutate(file);
                }}
              >
                <Field>
                  <FieldLabel htmlFor="csv-file">File CSV *</FieldLabel>
                  <Input ref={fileRef} id="csv-file" type="file" accept=".csv,text/csv" required />
                </Field>
                <p className="text-sm text-muted-foreground">
                  Cột: <code>source,content[,external_ref][,created_at]</code>. Dòng lỗi
                  không chặn dòng hợp lệ.
                </p>
                {importCsv.data ? (
                  <div className="rounded-md border p-3 text-sm">
                    <p>
                      Đã nhập: <b>{importCsv.data.imported}</b> · Lỗi:{" "}
                      <b>{importCsv.data.failed}</b>
                    </p>
                    {importCsv.data.errors.length > 0 ? (
                      <ul className="mt-2 max-h-32 overflow-auto text-muted-foreground">
                        {importCsv.data.errors.map((er) => (
                          <li key={er.row}>
                            Dòng {er.row}: {er.reason}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                <Button type="submit" disabled={importCsv.isPending}>
                  {importCsv.isPending ? <Spinner data-icon="inline-start" /> : null}
                  Import
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Wizard đăng ký nguồn 2 bước (FE-03b T2) */}
      <Dialog
        open={wizardOpen}
        onOpenChange={(o) => {
          setWizardOpen(o);
          if (!o) setWizardStep(1);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Đăng ký nguồn mới</DialogTitle>
            <DialogDescription>Bước {wizardStep}/2</DialogDescription>
          </DialogHeader>

          {wizardStep === 1 ? (
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                setDraft({
                  name: String(f.get("name") ?? "").trim(),
                  description: String(f.get("description") ?? "").trim(),
                });
                setWizardStep(2);
              }}
            >
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="new-source-name">Tên nguồn *</FieldLabel>
                  <Input
                    id="new-source-name"
                    name="name"
                    required
                    maxLength={100}
                    placeholder="google_play, khảo sát nội bộ…"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="new-source-desc">Mô tả (tuỳ chọn)</FieldLabel>
                  <Input
                    id="new-source-desc"
                    name="description"
                    maxLength={500}
                    placeholder="Nguồn này dùng để làm gì?"
                  />
                </Field>
              </FieldGroup>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setWizardOpen(false)}>
                  Huỷ
                </Button>
                <Button type="submit">Tiếp tục</Button>
              </div>
            </form>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="rounded-md border p-3 text-sm">
                <p>
                  Tên: <b>{draft.name}</b>
                </p>
                {draft.description ? (
                  <p className="text-muted-foreground">Mô tả: {draft.description}</p>
                ) : null}
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setWizardStep(1)}>
                  ← Sửa lại
                </Button>
                <Button
                  disabled={createSource.isPending}
                  onClick={() =>
                    createSource.mutate(
                      {
                        name: draft.name,
                        description: draft.description || undefined,
                      },
                      {
                        onSuccess: (created) => {
                          toast.success(`Đã đăng ký nguồn "${created.name}".`);
                          setSourceValue(created.name);
                          setWizardOpen(false);
                          setWizardStep(1);
                        },
                        onError: (e) =>
                          toast.error(
                            e instanceof ApiError ? e.message : "Lỗi không rõ"
                          ),
                      }
                    )
                  }
                >
                  {createSource.isPending ? <Spinner data-icon="inline-start" /> : null}
                  Xác nhận đăng ký
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

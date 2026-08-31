"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { useCreateImport } from "@/hooks/use-imports";
import { useProducts } from "@/hooks/use-products";
import { ApiError } from "@/lib/api";

export function CsvImportWizard({ onProfiled }: { onProfiled: (importId: string) => void }) {
  const products = useProducts();
  const createImport = useCreateImport();
  const [file, setFile] = useState<File | null>(null);
  const [productId, setProductId] = useState("");
  const effectiveProductId = productId || products.data?.items[0]?.id || "";

  function upload() {
    if (!file) return toast.error("Hãy chọn file CSV.");
    if (!effectiveProductId) return toast.error("Chưa có product nào.");
    createImport.mutate(
      { file, productId: effectiveProductId },
      {
        onSuccess: (result) => {
          toast.success("Đã tạo preview miễn phí", { description: "AI chưa được gọi." });
          onProfiled(result.id);
        },
        onError: (error) => toast.error(error instanceof ApiError ? error.message : "Upload thất bại"),
      },
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="import-file">File CSV *</FieldLabel>
          <Input id="import-file" type="file" accept=".csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </Field>
        <Field>
          <FieldLabel>Product đích</FieldLabel>
          <Select value={effectiveProductId} onValueChange={setProductId}>
            <SelectTrigger className="w-full"><SelectValue placeholder="Product…" /></SelectTrigger>
            <SelectContent>{(products.data?.items ?? []).map((product) => <SelectItem key={product.id} value={product.id}>{product.name}</SelectItem>)}</SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">Bước này chỉ đọc cấu trúc và tạo sample đã sanitize. Bạn sẽ review preview trong Activity Center trước khi quyết định gọi AI.</p>
        </Field>
      </FieldGroup>
      <Button onClick={upload} disabled={createImport.isPending}>
        {createImport.isPending ? <Spinner data-icon="inline-start" /> : null}
        Tải lên &amp; preview miễn phí
      </Button>
    </div>
  );
}

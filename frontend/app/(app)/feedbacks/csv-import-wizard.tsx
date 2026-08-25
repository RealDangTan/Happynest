"use client";
import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Papa from "papaparse";
import { toast } from "sonner";
import {
  Field,
  FieldGroup,
  FieldDescription,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { ImportCsvResult } from "@/lib/types";
import {
  CANON_HEADERS,
  guessAll,
  TARGETS,
  type TargetField,
} from "@/lib/csv-mapping";

// FE-03b T4: chuẩn hoá raw CSV phía client — map cột file sang trường chuẩn
// rồi serialize lại đúng header endpoint cũ (BE import KHÔNG đổi).

export function CsvImportWizard({ onImported }: { onImported: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<"pick" | "map">("pick");
  const [file, setFile] = useState<File | null>(null);
  const [fields, setFields] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [mapping, setMapping] = useState<Partial<Record<TargetField, string>>>({});
  const [result, setResult] = useState<ImportCsvResult | null>(null);

  function reset() {
    setStep("pick");
    setFile(null);
    setFields([]);
    setRows([]);
    setMapping({});
    setResult(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  function parseFile(f: File) {
    // Dataset demo ≤1500 rows — parse cả file vào bộ nhớ là đủ.
    Papa.parse<Record<string, string>>(f, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const parsedFields = res.meta.fields ?? [];
        if (parsedFields.length === 0 || res.data.length === 0) {
          toast.error("File rỗng hoặc không đọc được header CSV.");
          return;
        }
        setFile(f);
        setFields(parsedFields);
        setRows(res.data);
        setMapping(guessAll(parsedFields));
        setResult(null);
        setStep("map");
      },
      error: (err) =>
        toast.error(`Không đọc được file: ${err.message}`),
    });
  }

  const importCsv = useMutation({
    mutationFn: async (payload: File) => {
      const fd = new FormData();
      fd.append("file", payload);
      // KHÔNG set Content-Type tay — trình duyệt tự thêm boundary multipart.
      return apiFetch<ImportCsvResult>("/api/feedbacks/import-csv", {
        method: "POST",
        body: fd,
      });
    },
    onSuccess: (r) => {
      toast.success(`Import xong: ${r.imported} dòng mới, ${r.failed} lỗi.`);
      setResult(r);
      onImported();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Lỗi không rõ"),
  });

  const missingRequired = TARGETS.filter(
    (t) => t.required && !mapping[t.key],
  );

  function transformRow(row: Record<string, string>): Record<string, string> {
    return Object.fromEntries(
      TARGETS.map(({ key }) => {
        const col = mapping[key];
        return [key, (col ? row[col] : "") ?? ""];
      }),
    );
  }

  function doImport() {
    if (!file) return;
    const canonical = Papa.unparse({
      fields: CANON_HEADERS,
      data: rows.map(transformRow).map((r) => CANON_HEADERS.map((h) => r[h])),
    });
    importCsv.mutate(new File([canonical], `mapped-${file.name}`, { type: "text/csv" }));
  }

  if (step === "pick") {
    return (
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const f = fileRef.current?.files?.[0];
          if (f) parseFile(f);
        }}
      >
        <Field>
          <FieldLabel htmlFor="csv-file">File CSV *</FieldLabel>
          <Input ref={fileRef} id="csv-file" type="file" accept=".csv,text/csv" required />
          <FieldDescription>
            Bước 1/2 — sau khi chọn file bạn sẽ map cột của file sang trường chuẩn
            (không cần sửa file trước khi đưa lên).
          </FieldDescription>
        </Field>
        <Button type="submit">Phân tích file</Button>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Bước 2/2 — file <b>{file?.name}</b>: {rows.length} dòng,{" "}
        {fields.length} cột. Gán cột file sang trường chuẩn:
      </p>
      <FieldGroup>
        {TARGETS.map(({ key, label, required }) => (
          <Field key={key}>
            <FieldLabel htmlFor={`map-${key}`}>
              {label}
              {required ? " *" : ""}
            </FieldLabel>
            <Select
              value={mapping[key] ?? "__none__"}
              onValueChange={(v) =>
                setMapping((m) => ({ ...m, [key]: v === "__none__" ? undefined : v }))
              }
            >
              <SelectTrigger id={`map-${key}`} className="w-full">
                <SelectValue placeholder="— Bỏ qua —" />
              </SelectTrigger>
              <SelectContent>
                {!required ? (
                  <SelectItem value="__none__">— Bỏ qua —</SelectItem>
                ) : null}
                {fields.map((f) => (
                  <SelectItem key={f} value={f}>
                    {f}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        ))}
      </FieldGroup>

      {/* Preview 5 dòng đầu đã transform */}
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {CANON_HEADERS.map((h) => (
                <TableHead key={h}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.slice(0, 5).map((row, i) => {
              const t = transformRow(row);
              return (
                <TableRow key={i}>
                  {CANON_HEADERS.map((h) => (
                    <TableCell key={h} className="max-w-[12rem] truncate">
                      {t[h] || (
                        <span className="text-muted-foreground">(trống)</span>
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {result ? (
        <div className="rounded-md border p-3 text-sm">
          <p>
            Đã nhập: <b>{result.imported}</b> · Lỗi: <b>{result.failed}</b>
          </p>
          {result.errors.length > 0 ? (
            <ul className="mt-2 max-h-32 overflow-auto text-muted-foreground">
              {result.errors.map((er) => (
                <li key={er.row}>
                  Dòng {er.row}: {er.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="flex justify-between gap-2">
        <Button variant="ghost" onClick={reset}>
          ← Chọn file khác
        </Button>
        {result ? null : (
          <Button onClick={doImport} disabled={missingRequired.length > 0 || importCsv.isPending}>
            {importCsv.isPending ? <Spinner data-icon="inline-start" /> : null}
            {missingRequired.length > 0
              ? `Thiếu map: ${missingRequired.map((t) => t.label).join(", ")}`
              : `Import ${rows.length} dòng`}
          </Button>
        )}
      </div>
    </div>
  );
}

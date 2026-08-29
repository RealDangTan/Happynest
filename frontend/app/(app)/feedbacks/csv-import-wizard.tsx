"use client";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError } from "@/lib/api";
import type {
  HumanMappingAction,
  ImportApplyReport,
  MappingDecision,
  MappingItem,
} from "@/lib/types";
import {
  useCreateImport,
  useDecideMapping,
  useGetMapping,
} from "@/hooks/use-imports";
import { useProducts } from "@/hooks/use-products";

type Step = "pick" | "review" | "done";

const DECISION_LABEL: Record<string, string> = {
  MAP: "MAP",
  PROMOTE: "PROMOTE (field mới)",
  SOURCE_META: "SOURCE_META",
  IGNORE: "IGNORE",
  AMBIGUOUS: "AMBIGUOUS — cần bạn quyết",
};

/** Màu badge theo độ tin cậy của proposal LLM. */
function confidenceVariant(c: number): "default" | "secondary" | "destructive" {
  if (c >= 0.8) return "default";
  if (c >= 0.5) return "secondary";
  return "destructive";
}

export function CsvImportWizard({ onImported }: { onImported: () => void }) {
  const products = useProducts();
  const [step, setStep] = useState<Step>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const [report, setReport] = useState<ImportApplyReport | null>(null);

  // Gate #1 state: action human chọn per source_field
  const [actions, setActions] = useState<
    Record<string, { action: HumanMappingAction; targetKey?: string }>
  >({});

  const createImport = useCreateImport();
  const mapping = useGetMapping(importId);
  const decide = useDecideMapping();

  const productId =
    (products.data?.items ?? [])[0]?.id ?? "";

  const defaultActionFor = (m: MappingItem): HumanMappingAction =>
    m.decision === "AMBIGUOUS" ? "ignore" : "approve";

  const items = mapping.data?.mappings ?? [];
  const allDecided = useMemo(
    () => items.every((m) => actions[m.source_field]?.action),
    [items, actions],
  );

  function startUpload() {
    if (!file) {
      toast.error("Hãy chọn file CSV.");
      return;
    }
    if (!productId) {
      toast.error("Chưa có product nào — tạo product trước.");
      return;
    }
    createImport.mutate(
      { file, productId },
      {
        onSuccess: (imp) => {
          setImportId(imp.id);
          setStep("review");
        },
        onError: (e) =>
          toast.error(e instanceof ApiError ? e.message : "Upload thất bại"),
      },
    );
  }

  function submitDecisions() {
    if (!importId) return;
    const decisions: MappingDecision[] = items.map((m) => ({
      source_field: m.source_field,
      action: actions[m.source_field]?.action ?? defaultActionFor(m),
      ...(actions[m.source_field]?.targetKey
        ? { target_key: actions[m.source_field].targetKey }
        : {}),
    }));
    decide.mutate(
      { importId, decisions },
      {
        onSuccess: (rep) => {
          setReport(rep);
          setStep("done");
          onImported();
        },
        onError: (e) =>
          toast.error(e instanceof ApiError ? e.message : "Import thất bại"),
      },
    );
  }

  // ---------------------------------------------------------------- step 1
  if (step === "pick") {
    return (
      <div className="flex flex-col gap-4">
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="import-file">File CSV *</FieldLabel>
            <Input
              id="import-file"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </Field>
          <Field>
            <FieldLabel>Product đích</FieldLabel>
            <Select value={productId} onValueChange={() => undefined}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Product…" />
              </SelectTrigger>
              <SelectContent>
                {(products.data?.items ?? []).map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              AI sẽ đọc profile từng cột và đề xuất cách map vào product schema —
              bạn duyệt trước khi dữ liệu được nạp.
            </p>
          </Field>
        </FieldGroup>
        <Button onClick={startUpload} disabled={createImport.isPending}>
          {createImport.isPending ? (
            <Spinner data-icon="inline-start" />
          ) : null}
          Phân tích &amp; đề xuất mapping
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------- step 2
  if (step === "review") {
    return (
      <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto pr-1">
        {mapping.isPending ? <Spinner /> : null}
        {mapping.data ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cột CSV</TableHead>
                <TableHead>Đề xuất AI</TableHead>
                <TableHead>Tin cậy</TableHead>
                <TableHead>Quyết định của bạn</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((m) => {
                const act = actions[m.source_field]?.action;
                return (
                  <TableRow key={m.source_field}>
                    <TableCell className="font-medium">
                      {m.source_field}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-0.5">
                        <span>{DECISION_LABEL[m.decision] ?? m.decision}</span>
                        {m.target ? (
                          <span className="text-xs text-muted-foreground">
                            → {m.target}
                          </span>
                        ) : null}
                        {m.candidate ? (
                          <span className="text-xs text-muted-foreground">
                            → field mới: {m.candidate.key} ({m.candidate.type})
                          </span>
                        ) : null}
                        <span className="text-xs text-muted-foreground">
                          {m.reason}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={confidenceVariant(m.confidence)}>
                        {Math.round(m.confidence * 100)}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <Select
                          value={act ?? defaultActionFor(m)}
                          onValueChange={(v) =>
                            setActions((prev) => ({
                              ...prev,
                              [m.source_field]: {
                                action: v as HumanMappingAction,
                                targetKey: prev[m.source_field]?.targetKey,
                              },
                            }))
                          }
                        >
                          <SelectTrigger className="w-40">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="approve">Duyệt đề xuất</SelectItem>
                            <SelectItem value="remap">Map sang field khác…</SelectItem>
                            <SelectItem value="demote">Để source metadata</SelectItem>
                            <SelectItem value="ignore">Bỏ qua cột</SelectItem>
                          </SelectContent>
                        </Select>
                        {actions[m.source_field]?.action === "remap" ? (
                          <Input
                            placeholder="key đích (vd: app_version)"
                            value={actions[m.source_field]?.targetKey ?? ""}
                            onChange={(e) =>
                              setActions((prev) => ({
                                ...prev,
                                [m.source_field]: {
                                  action: "remap",
                                  targetKey: e.target.value,
                                },
                              }))
                            }
                          />
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        ) : null}

        {items.some((m) => m.decision === "AMBIGUOUS") ? (
          <Alert>
            <AlertTitle>Có cột AMBIGUOUS</AlertTitle>
            <AlertDescription>
              AI không chắc nghĩa của một số cột (ví dụ cột “score” — CSAT hay
              NPS?). Hãy chọn “Bỏ qua” hoặc “Map sang field khác…” cho các cột
              này — hệ thống không cho phép duyệt máy móc.
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setStep("pick")}>
            ← Chọn file khác
          </Button>
          <Button onClick={submitDecisions} disabled={!allDecided || decide.isPending}>
            {decide.isPending ? <Spinner data-icon="inline-start" /> : null}
            Duyệt &amp; import
          </Button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------- step 3
  return (
    <Card>
      <CardHeader>
        <CardTitle>Import hoàn tất</CardTitle>
        <CardDescription>
          {report
            ? `Đã nạp ${report.imported} dòng (lỗi: ${report.failed}) — schema v${report.schema_version ?? "?"}.`
            : "Không có kết quả."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {report && report.errors.length > 0 ? (
          <div className="max-h-40 overflow-y-auto rounded-md border p-2 text-xs">
            {report.errors.map((e) => (
              <p key={e.row}>
                Dòng {e.row}: {e.reason}
              </p>
            ))}
          </div>
        ) : null}
        <Button
          variant="outline"
          onClick={() => {
            setStep("pick");
            setFile(null);
            setImportId(null);
            setReport(null);
            setActions({});
          }}
        >
          Import file khác
        </Button>
      </CardContent>
    </Card>
  );
}

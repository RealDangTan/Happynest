"use client";
import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  Inbox,
  Play,
  TriangleAlert,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  apiFetch,
  ApiError,
} from "@/lib/api";
import type {
  HumanMappingAction,
  ImportListResponse,
  MappingDecision,
  MappingItem,
} from "@/lib/types";
import {
  useCreateImport,
  useDecideMapping,
  useGetMapping,
  useImport,
  useImportPreview,
  useProposeMapping,
} from "@/hooks/use-imports";
import { useProduct } from "@/hooks/use-product";
import { FirstRunGuide } from "@/components/onboarding/first-run-guide";
import { PageHeader } from "@/components/page-header";

const SOURCE_TILES = ["Survey app", "App store", "Support inbox", "NPS tool"];

const STATUS_BADGE: Record<string, { label: string; tone: "secondary" | "default" | "destructive" | "outline" }> = {
  profile_ready: { label: "Needs mapping review", tone: "default" },
  mapping_generating: { label: "Proposing mapping", tone: "secondary" },
  mapping_review: { label: "Needs mapping review", tone: "default" },
  importing: { label: "Importing", tone: "secondary" },
  imported: { label: "Imported", tone: "outline" },
  failed: { label: "Failed", tone: "destructive" },
  cancelled: { label: "Cancelled", tone: "outline" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_BADGE[status] ?? { label: status, tone: "secondary" as const };
  return <Badge variant={s.tone}>{s.label}</Badge>;
}

function useProductImports(productId: string | null) {
  return useQuery({
    queryKey: ["imports", "product", productId],
    queryFn: () =>
      apiFetch<ImportListResponse>(
        `/api/imports?limit=50&product_id=${productId}`,
      ),
    enabled: productId != null,
    refetchInterval: 5000,
    staleTime: 0,
  });
}

type Phase = "idle" | "file" | "preview" | "mapping" | "result";

const STEPS: { key: Phase; label: string }[] = [
  { key: "file", label: "File" },
  { key: "preview", label: "Preview" },
  { key: "mapping", label: "Mapping" },
  { key: "result", label: "Result" },
];

function Stepper({ current }: { current: Phase }) {
  const index = STEPS.findIndex((s) => s.key === current);
  return (
    <ol className="flex items-center gap-2 text-sm" aria-label="Import steps">
      {STEPS.map((step, i) => (
        <li key={step.key} className="flex items-center gap-2">
          <span
            className={
              i === index
                ? "font-semibold text-foreground"
                : i < index
                  ? "text-lichen"
                  : "text-muted-foreground"
            }
            aria-current={i === index ? "step" : undefined}
          >
            {step.label}
          </span>
          {i < STEPS.length - 1 ? <span className="text-muted-foreground">—</span> : null}
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------- Step 1: File

function StepFile({
  productReady,
  onUploaded,
  onCancel,
}: {
  productReady: boolean;
  onUploaded: (importId: string) => void;
  onCancel: () => void;
}) {
  const createImport = useCreateImport();
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { productId } = useProduct();

  const upload = async () => {
    if (!file || !productId) return;
    try {
      const created = await createImport.mutateAsync({ file, productId });
      toast.success("Preview ready — no AI used yet.");
      onUploaded(created.id);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not upload the file",
      );
    }
  };

  return (
    <section className="mx-auto max-w-xl space-y-6 py-10">
      <div
        className="rounded-lg border-2 border-dashed border-border bg-card p-8 text-center"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const dropped = e.dataTransfer.files?.[0];
          if (dropped) setFile(dropped);
        }}
      >
        <Upload className="mx-auto mb-3 size-8 text-muted-foreground" />
        <p className="text-sm">
          Drop a CSV here, or{" "}
          <button
            className="font-medium text-signal underline underline-offset-4"
            onClick={() => inputRef.current?.click()}
          >
            Choose file
          </button>
        </p>
        {file ? (
          <p className="mt-2 flex items-center justify-center gap-2 text-sm font-medium">
            <FileSpreadsheet className="size-4" /> {file.name}
          </p>
        ) : null}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {!productReady ? (
          <p className="mt-3 text-sm text-destructive">
            Choose a product first — the header dropdown lists your products.
          </p>
        ) : null}
      </div>
      <p className="text-sm text-muted-foreground">
        File errors appear here, with a specific correction.
      </p>
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          disabled={!file || !productReady || createImport.isPending}
          onClick={() => void upload()}
        >
          {createImport.isPending ? <Spinner data-icon="inline-start" /> : null}
          Upload and preview
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- Step 2: Preview

function StepPreview({
  importId,
  onBack,
  onProposed,
}: {
  importId: string;
  onBack: () => void;
  onProposed: () => void;
}) {
  const preview = useImportPreview(importId);
  const detail = useImport(importId);
  const propose = useProposeMapping();

  // After the paid proposal is accepted, useImport polls every 2s while the
  // mapping is generating; the parent moves to the mapping step when the
  // status becomes mapping_review.

  return (
    <section className="space-y-6">
      {detail.data?.status === "mapping_generating" ? (
        <Alert>
          <Play className="size-4" />
          <AlertTitle>AI is proposing column meanings</AlertTitle>
          <AlertDescription>
            Only the sanitized profile and samples are sent — never the raw
            file. You can leave this screen; the task stays in Current tasks.
          </AlertDescription>
        </Alert>
      ) : null}
      {detail.data?.error ? (
        <Alert variant="destructive">
          <TriangleAlert className="size-4" />
          <AlertTitle>Last attempt failed</AlertTitle>
          <AlertDescription>{detail.data.error}</AlertDescription>
        </Alert>
      ) : null}
      {preview.isPending ? (
        <Spinner />
      ) : preview.isError ? (
        <Alert variant="destructive">
          <TriangleAlert className="size-4" />
          <AlertTitle>Could not load the preview</AlertTitle>
          <AlertDescription>
            {preview.error.message} — the sanitized profile is still on the
            server.
          </AlertDescription>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 w-fit"
            onClick={() => void preview.refetch()}
          >
            Retry
          </Button>
        </Alert>
      ) : preview.data ? (
        <>
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h2 className="font-heading text-lg">
              {preview.data.original_filename ?? "CSV"}
            </h2>
            <span className="font-mono text-sm text-muted-foreground">
              {preview.data.source_row_count} rows · {preview.data.column_profiles.length}{" "}
              columns
            </span>
            <Badge variant="outline">No AI used yet. Samples below are sanitized.</Badge>
          </div>
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Sample (sanitized)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.data.column_profiles.map((column) => (
                  <TableRow key={column.name}>
                    <TableCell className="break-words font-medium">{column.name}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {column.detected_type ?? "—"}
                    </TableCell>
                    <TableCell className="max-w-sm break-words text-muted-foreground">
                      {column.sample_values?.join(" · ") || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-sm text-muted-foreground">
            Review the structure before asking AI to propose column meanings.
          </p>
        </>
      ) : null}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft data-icon="inline-start" />
          Back to file
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button disabled={!preview.data}>
              Suggest mapping
              <ArrowRight data-icon="inline-end" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Review expected usage</AlertDialogTitle>
              <AlertDialogDescription>
                One logical mapping job. Only the sanitized profile and sample
                values are sent to the provider. You confirm the result next.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Back</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  propose.mutate(importId, {
                    onSuccess: onProposed,
                    onError: (err) =>
                      toast.error(
                        err instanceof ApiError ? err.message : "Could not start mapping",
                      ),
                  })
                }
              >
                Start mapping proposal
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- Step 3: Mapping (G1)

const CORE_TARGETS = [
  { key: "feedback_text", label: "Feedback text" },
  { key: "occurred_at", label: "Feedback date" },
  { key: "source", label: "Source metadata" },
];

function meaningLabel(entry: MappingItem): string {
  if (entry.target) {
    const core = CORE_TARGETS.find((c) => c.key === entry.target);
    if (core) return core.label;
  }
  if (entry.candidate?.label) return `Product field: ${entry.candidate.label}`;
  if (entry.decision === "AMBIGUOUS") return "Ambiguous — resolve below";
  return "Ignore";
}

function StepMapping({
  importId,
  onBack,
  onDecided,
}: {
  importId: string;
  onBack: () => void;
  onDecided: () => void;
}) {
  const mapping = useGetMapping(importId);
  const decide = useDecideMapping();
  const [actions, setActions] = useState<
    Record<string, { action: HumanMappingAction; targetKey?: string }>
  >({});
  const mappings = mapping.data?.mappings ?? [];
  const defaultAction = (entry: MappingItem): HumanMappingAction =>
    entry.decision === "AMBIGUOUS" ? "ignore" : "approve";

  const ambiguous = mappings.filter(
    (e) => (actions[e.source_field]?.action ?? defaultAction(e)) !== "approve",
  );

  const submit = () => {
    const decisions: MappingDecision[] = mappings.map((entry) => {
      const override = actions[entry.source_field];
      const action = override?.action ?? defaultAction(entry);
      const targetKey =
        action === "remap" || action === "promote"
          ? override?.targetKey ?? entry.candidate?.key ?? null
          : null;
      return {
        source_field: entry.source_field,
        action,
        target_key: targetKey,
      };
    });
    decide.mutate(
      { importId, decisions },
      {
        onSuccess: onDecided,
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Import could not start"),
      },
    );
  };

  return (
    <section className="space-y-6">
      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-40">CSV column</TableHead>
              <TableHead className="w-64">Product meaning</TableHead>
              <TableHead>Sample</TableHead>
              <TableHead className="w-24">Review</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mapping.isPending ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Spinner />
                </TableCell>
              </TableRow>
            ) : (
              mappings.map((entry) => {
                const override = actions[entry.source_field];
                const current = override?.action ?? defaultAction(entry);
                return (
                  <TableRow key={entry.source_field}>
                    <TableCell className="break-words font-mono text-xs font-medium">
                      {entry.source_field}
                    </TableCell>
                    <TableCell>
                      <Select
                        value={current}
                        onValueChange={(value) =>
                          setActions((old) => ({
                            ...old,
                            [entry.source_field]: {
                              action: value as HumanMappingAction,
                              targetKey: old[entry.source_field]?.targetKey,
                            },
                          }))
                        }
                      >
                        <SelectTrigger className="w-56">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="approve">
                            Keep AI meaning · {meaningLabel(entry)}
                          </SelectItem>
                          {CORE_TARGETS.map((c) => (
                            <SelectItem key={c.key} value="remap">
                              Map to {c.label}
                            </SelectItem>
                          ))}
                          <SelectItem value="promote">Product field…</SelectItem>
                          <SelectItem value="demote">Source metadata</SelectItem>
                          <SelectItem value="ignore">Ignore</SelectItem>
                        </SelectContent>
                      </Select>
                      {current === "remap" ? (
                        <Input
                          className="mt-2"
                          placeholder="target_key (e.g. feedback_text)"
                          value={override?.targetKey ?? ""}
                          onChange={(event) =>
                            setActions((old) => ({
                              ...old,
                              [entry.source_field]: {
                                action: "remap",
                                targetKey: event.target.value,
                              },
                            }))
                          }
                        />
                      ) : null}
                      {current === "promote" && entry.candidate ? (
                        <Select
                          value={override?.targetKey ?? entry.candidate.key}
                          onValueChange={(value) =>
                            setActions((old) => ({
                              ...old,
                              [entry.source_field]: { action: "promote", targetKey: value },
                            }))
                          }
                        >
                          <SelectTrigger className="mt-2 w-56">
                            <SelectValue placeholder="Choose product field" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={entry.candidate.key}>
                              {entry.candidate.label}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      ) : null}
                    </TableCell>
                    <TableCell className="max-w-xs break-words text-muted-foreground">
                      {entry.candidate?.description ?? entry.reason ?? "—"}
                    </TableCell>
                    <TableCell>
                      {current === "approve" ? (
                        <span className="text-sm text-lichen">Ready</span>
                      ) : (
                        <span className="text-sm font-medium text-warning">Changed</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <Alert>
        <AlertTitle>G1 — Confirm what these columns mean</AlertTitle>
        <AlertDescription>
          Resolve ambiguous mappings and missing required fields before importing.
          {ambiguous.length > 0
            ? ` ${ambiguous.length} column(s) changed from the AI proposal.`
            : " The AI proposal is accepted as shown."}
        </AlertDescription>
      </Alert>

      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft data-icon="inline-start" />
          Back to preview
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button disabled={decide.isPending || mappings.length === 0}>
              Confirm mapping &amp; import
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>G1 — Confirm mapping &amp; import?</AlertDialogTitle>
              <AlertDialogDescription>
                Import runs in the background and writes sanitized feedback only.
                Analysis never starts automatically.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Check again</AlertDialogCancel>
              <AlertDialogAction onClick={submit}>Confirm &amp; import</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- Step 4: Result

function StepResult({ importId }: { importId: string }) {
  const detail = useImport(importId);
  const item = detail.data;
  if (!item) return <Spinner />;

  if (item.status === "importing") {
    return (
      <section className="mx-auto max-w-xl space-y-4 py-10">
        <h2 className="font-heading text-xl">Importing…</h2>
        {/* No honest % exists server-side yet — spin instead of faking progress. */}
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Sanitizing rows and storing them…
        </p>
        <p className="text-sm text-muted-foreground">
          You can leave this screen. Reopen the task from Current tasks.
        </p>
      </section>
    );
  }

  if (item.status === "failed") {
    return (
      <section className="mx-auto max-w-xl space-y-4 py-10">
        <Alert variant="destructive">
          <TriangleAlert className="size-4" />
          <AlertTitle>Import failed</AlertTitle>
          <AlertDescription>{item.error ?? "Unknown error"}</AlertDescription>
        </Alert>
        <Button variant="outline" asChild>
          <Link href="/importer">Import another file</Link>
        </Button>
      </section>
    );
  }

  // Defense-in-depth: only a genuinely imported import may show the summary —
  // a pre-import status (mapping_review / profile_ready) landing here must
  // never render a phantom "0 imported" card.
  if (item.status !== "imported") {
    return (
      <section className="mx-auto max-w-xl space-y-4 py-10">
        <h2 className="font-heading text-xl">Import still in review</h2>
        <p className="text-sm text-muted-foreground">
          This import has not run yet — confirm its column mapping first.
        </p>
        <Button variant="outline" asChild>
          <Link href="/importer">Back to the Importer</Link>
        </Button>
      </section>
    );
  }

  const report = item.report;
  return (
    <section className="mx-auto max-w-xl space-y-6 py-10">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="size-5 text-lichen" />
        <h2 className="font-heading text-xl">Import completed</h2>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg border bg-card p-4">
          <p className="font-mono text-2xl font-semibold">
            {item.source_row_count ?? item.row_count ?? 0}
          </p>
          <p className="text-xs text-muted-foreground">source rows</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <p className="font-mono text-2xl font-semibold text-lichen">
            {report?.imported ?? item.row_count ?? 0}
          </p>
          <p className="text-xs text-muted-foreground">imported</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <p
            className={`font-mono text-2xl font-semibold ${
              (report?.failed ?? 0) > 0 ? "text-destructive" : ""
            }`}
          >
            {report?.failed ?? 0}
          </p>
          <p className="text-xs text-muted-foreground">failed</p>
        </div>
      </div>
      {report && report.errors.length > 0 ? (
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm font-medium">Row errors</p>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {report.errors.slice(0, 10).map((e, i) => (
              <li key={`${e.row}-${i}`} className="break-words font-mono text-xs">
                Row {e.row}: {e.reason}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            Correct and re-import only the failed rows.
          </p>
        </div>
      ) : null}
      <div className="flex items-center justify-between">
        <Button variant="ghost" asChild>
          <Link href="/importer">Import another file</Link>
        </Button>
        <Button asChild>
          <Link href={`/vault?import=${importId}`}>Open Feedback Vault</Link>
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- S01 screen

export default function ImporterPage() {
  const { product, productId } = useProduct();
  const imports = useProductImports(productId);
  const [phase, setPhase] = useState<Phase>("idle");
  const [importId, setImportId] = useState<string | null>(null);
  const wizardImport = useImport(importId);

  // Proposal accepted → the mapping review (G1) replaces the preview step.
  // Also re-route stale phases: a saved "result" phase for an import that is
  // still pre-import must never show the "Import completed" card.
  const status = wizardImport.data?.status;
  const effectivePhase: Phase =
    status === "mapping_review" && (phase === "preview" || phase === "result")
      ? "mapping"
      : status === "profile_ready" && phase === "result"
        ? "preview"
        : phase;

  const recent = useMemo(() => {
    const items = imports.data?.items ?? [];
    return items.filter((i) =>
      ["profile_ready", "mapping_generating", "mapping_review", "failed"].includes(i.status),
    );
  }, [imports.data]);

  const history = useMemo(() => {
    const items = imports.data?.items ?? [];
    return items.filter((i) => ["imported", "cancelled"].includes(i.status));
  }, [imports.data]);

  // "file" phase has no importId yet — it is set by the upload callback before
  // preview/mapping/result, which always run with a valid importId.
  if (effectivePhase !== "idle" && (effectivePhase === "file" || importId)) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={() => setPhase("idle")}>
            <ArrowLeft data-icon="inline-start" />
            Importer
          </Button>
          <Stepper current={effectivePhase} />
        </div>
        <p className="text-sm text-muted-foreground">Product: {product?.name ?? "…"}</p>
        {effectivePhase === "file" ? (
          <StepFile
            productReady={Boolean(productId)}
            onUploaded={(id) => {
              setImportId(id);
              setPhase("preview");
            }}
            onCancel={() => setPhase("idle")}
          />
        ) : null}
        {effectivePhase === "preview" && importId ? (
          <StepPreview
            importId={importId}
            onBack={() => setPhase("file")}
            onProposed={() => setPhase("mapping")}
          />
        ) : null}
        {effectivePhase === "mapping" && importId ? (
          <StepMapping
            importId={importId}
            onBack={() => setPhase("preview")}
            onDecided={() => setPhase("result")}
          />
        ) : null}
        {effectivePhase === "result" && importId ? (
          <StepResult importId={importId} />
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <FirstRunGuide onStartImport={() => setPhase("file")} />

      <PageHeader
        title="Bring feedback into your product."
        actions={
          <p className="font-mono text-sm text-muted-foreground">
            Product: {product?.name ?? "—"}
          </p>
        }
      />

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-8">
          <section className="rounded-xl border bg-card px-6 py-10 text-center sm:px-10">
            <Button size="lg" onClick={() => setPhase("file")} disabled={!productId}>
              <Inbox data-icon="inline-start" />
              Import CSV
            </Button>
            <div className="mx-auto mt-6 grid max-w-md grid-cols-2 gap-3">
              {SOURCE_TILES.map((tile) => (
                <div
                  key={tile}
                  className="rounded-lg border bg-secondary/50 p-3 text-sm text-muted-foreground"
                  title="Coming later"
                >
                  {tile}
                  <span className="ml-1 text-xs">(coming later)</span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              CSV is the supported source. Additional sources are placeholders.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Current tasks — imports
            </h2>
            {recent.length ? (
              <div className="space-y-3">
                {recent.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3"
                  >
                    <FileSpreadsheet className="size-4 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {item.original_filename ?? item.id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.source_row_count ?? item.row_count ?? 0} rows
                      </p>
                    </div>
                    <StatusBadge status={item.status} />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setImportId(item.id);
                        setPhase(
                          item.status === "mapping_review"
                            ? "mapping"
                            : item.status === "profile_ready"
                              ? "preview"
                              : "result",
                        );
                      }}
                    >
                      Continue mapping
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <Empty className="border">
                <EmptyHeader>
                  <EmptyTitle>No imports waiting</EmptyTitle>
                  <EmptyDescription>Import a CSV to get started.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Recent imports
            </h2>
            {history.length ? (
              <div className="rounded-lg border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File</TableHead>
                      <TableHead>Rows</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">
                          {item.original_filename ?? item.id}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {item.row_count ?? item.source_row_count ?? "—"}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={item.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" variant="outline" asChild>
                            <Link href={`/vault?import=${item.id}`}>Open</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No completed imports yet.
              </p>
            )}
          </section>
        </div>

        <aside className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            How it works
          </h2>
          <ol className="space-y-4 rounded-xl border bg-card p-5 text-sm leading-relaxed">
            <li>1. Upload a CSV — preview stays sanitized, no AI yet.</li>
            <li>2. AI proposes column meanings.</li>
            <li>
              <strong>G1</strong> — you confirm the mapping before anything imports.
            </li>
            <li>3. Import runs; row errors are reported per row.</li>
            <li>4. Continue in the Feedback Vault.</li>
          </ol>
          {history.length ? (
            <Button variant="ghost" size="sm" asChild>
              <Link href="/vault">
                Open Feedback Vault
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

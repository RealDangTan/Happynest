"use client"
import { useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  Play,
  TriangleAlert,
  Upload,
} from "lucide-react"
import { toast } from "sonner"
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { ImportRecord, MappingDecision, MappingItem } from "@/lib/types"
import {
  useActiveSchema,
} from "@/hooks/use-products"
import { useProduct } from "@/hooks/use-product"
import {
  useDecideMapping,
  useCreateImport,
  useGetMapping,
  useImport,
  useImportPreview,
  useProposeMapping,
} from "@/hooks/use-imports"
import { ApiError } from "@/lib/api"

export const IMPORT_STEPS = ["File", "Preview", "Mapping", "Result"] as const

export type Phase = "idle" | "file" | "preview" | "mapping" | "result"

export const PHASE_STEP: Record<Phase, (typeof IMPORT_STEPS)[number]> = {
  idle: "File",
  file: "File",
  preview: "Preview",
  mapping: "Mapping",
  result: "Result",
}

/** Bước wizard tương ứng với trạng thái server của một import — dùng khi mở
 * lại task từ Activity Center hoặc deep-link /importer?import=<id> thay vì đi
 * từ bước File. `failed` có report là hỏng lúc import (→ Result), không có
 * report là hỏng trước propose (→ Preview để thử lại). */
export function stepForImport(
  item: Pick<ImportRecord, "status" | "report">
): (typeof IMPORT_STEPS)[number] {
  switch (item.status) {
    case "profile_ready":
    case "mapping_generating":
      return "Preview"
    case "mapping_review":
      return "Mapping"
    case "failed":
      return item.report ? "Result" : "Preview"
    default:
      return "Result"
  }
}

export function phaseForImport(
  item: Parameters<typeof stepForImport>[0]
): Phase {
  const step = stepForImport(item)
  return step === "Preview" ? "preview" : step === "Mapping" ? "mapping" : "result"
}

// ---------------------------------------------------------------- Step 1: File

export function StepFile({
  productReady,
  onUploaded,
  onCancel,
}: {
  productReady: boolean
  onUploaded: (importId: string) => void
  onCancel: () => void
}) {
  const createImport = useCreateImport()
  const [file, setFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { productId } = useProduct()

  const upload = async () => {
    if (!file || !productId) return
    try {
      const created = await createImport.mutateAsync({ file, productId })
      toast.success("Preview ready — no AI used yet.")
      onUploaded(created.id)
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not upload the file"
      )
    }
  }

  return (
    <section className="mx-auto flex max-w-xl flex-col gap-6 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Tải CSV lên</CardTitle>
          <CardDescription>
            Preview chỉ dùng dữ liệu đã sanitize — chưa gọi AI.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="rounded-lg border-2 border-dashed border-border p-8 text-center"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const dropped = e.dataTransfer.files?.[0]
              if (dropped) setFile(dropped)
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
                Choose a product first — the header dropdown lists your
                products.
              </p>
            ) : null}
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            File errors appear here, with a specific correction.
          </p>
        </CardContent>
        <CardFooter className="justify-between">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            disabled={!file || !productReady || createImport.isPending}
            onClick={() => void upload()}
          >
            {createImport.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : null}
            Upload and preview
          </Button>
        </CardFooter>
      </Card>
    </section>
  )
}

// ---------------------------------------------------------------- Step 2: Preview

export function StepPreview({
  importId,
  onBack,
  onProposed,
}: {
  importId: string
  onBack?: () => void
  onProposed?: () => void
}) {
  const preview = useImportPreview(importId)
  const detail = useImport(importId)
  const propose = useProposeMapping()

  // After the paid proposal is accepted, useImport polls every 2s while the
  // mapping is generating; the parent moves to the mapping step when the
  // status becomes mapping_review.

  return (
    <section className="flex flex-col gap-6">
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
        <Card>
          <CardContent className="items-center p-8">
            <Spinner />
          </CardContent>
        </Card>
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
        <Card>
          <CardHeader>
            <CardTitle>{preview.data.original_filename ?? "CSV"}</CardTitle>
            <CardDescription className="font-mono text-xs">
              {preview.data.source_row_count} rows ·{" "}
              {preview.data.column_profiles.length} columns
            </CardDescription>
            <CardAction>
              <Badge variant="outline">
                No AI used yet. Samples sanitized.
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="p-0">
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
                    <TableCell className="font-medium break-words">
                      {column.name}
                    </TableCell>
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
          </CardContent>
          <CardFooter>
            <p className="text-xs text-muted-foreground">
              Review the structure before asking AI to propose column meanings.
            </p>
          </CardFooter>
        </Card>
      ) : null}
      <div className="flex items-center justify-between">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft data-icon="inline-start" />
            Back to file
          </Button>
        ) : (
          <span />
        )}
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
                    ...(onProposed ? { onSuccess: onProposed } : {}),
                    onError: (err) =>
                      toast.error(
                        err instanceof ApiError
                          ? err.message
                          : "Could not start mapping"
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
  )
}

// ---------------------------------------------------------------- Step 3: Mapping (G1)

const CORE_TARGET_LABELS: Record<string, string> = {
  feedback_text: "Feedback text",
  occurred_at: "Feedback date",
  source: "Source metadata",
  source_record_id: "Source record ID",
}

/** Quyết định người dùng trên mỗi hàng — "change" được dịch thành remap
 * (key đã có trong schema) hoặc promote (field mới) lúc submit. */
type RowAction = "approve" | "change" | "ignore"

function suggestView(entry: MappingItem): { key: string | null; note: string } {
  if (entry.decision === "AMBIGUOUS") return { key: null, note: "Ambiguous" }
  if (entry.target)
    return { key: entry.target, note: CORE_TARGET_LABELS[entry.target] ?? "" }
  if (entry.candidate)
    return { key: entry.candidate.key, note: "product field mới" }
  if (entry.decision === "SOURCE_META")
    return { key: null, note: "Source metadata" }
  return { key: null, note: "Ignore" }
}

function humanizeKey(key: string): string {
  return key
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function StepMapping({
  importId,
  onBack,
  onDecided,
}: {
  importId: string
  onBack?: () => void
  onDecided?: () => void
}) {
  const mapping = useGetMapping(importId)
  const decide = useDecideMapping()
  const { productId } = useProduct()
  const schema = useActiveSchema(productId)
  const [actions, setActions] = useState<
    Record<string, { action: RowAction; targetKey?: string }>
  >({})
  const mappings = mapping.data?.mappings ?? []
  const knownKeys = useMemo(() => {
    const core = schema.data?.core_fields.map((f) => f.key) ?? []
    const fields = schema.data?.schema?.definition.fields.map((f) => f.key) ?? []
    return new Set([...core, ...fields])
  }, [schema.data])

  const defaultAction = (entry: MappingItem): RowAction =>
    entry.decision === "AMBIGUOUS" ? "ignore" : "approve"

  const changed = mappings.filter((e) => {
    const override = actions[e.source_field]
    if (!override) return false
    return (
      override.action !== defaultAction(e) ||
      (override.targetKey ?? "").trim() !== ""
    )
  })
  // Change mà chưa nhập target_key → chặn confirm thay vì submit dở.
  const pendingChanges = mappings.filter((e) => {
    const override = actions[e.source_field]
    return (
      (override?.action ?? defaultAction(e)) === "change" &&
      (override?.targetKey ?? "").trim() === ""
    )
  })

  const submit = () => {
    const decisions: MappingDecision[] = mappings.map((entry) => {
      const override = actions[entry.source_field]
      const action = override?.action ?? defaultAction(entry)
      if (action === "change") {
        const key = (override?.targetKey ?? "").trim()
        if (knownKeys.has(key)) {
          return {
            source_field: entry.source_field,
            action: "remap",
            target_key: key,
          }
        }
        return {
          source_field: entry.source_field,
          action: "promote",
          candidate: {
            key,
            label: humanizeKey(key),
            description: null,
            type: "text" as const,
          },
        }
      }
      return {
        source_field: entry.source_field,
        action,
        target_key: null,
      }
    })
    decide.mutate(
      { importId, decisions },
      {
        ...(onDecided ? { onSuccess: onDecided } : {}),
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Import could not start"
          ),
      }
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <Card className="py-0">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-40">CSV column</TableHead>
                <TableHead className="w-44">AI column suggest</TableHead>
                <TableHead>Explain</TableHead>
                <TableHead className="w-56">Action</TableHead>
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
                  const override = actions[entry.source_field]
                  const current = override?.action ?? defaultAction(entry)
                  const suggest = suggestView(entry)
                  const typedKey = (override?.targetKey ?? "").trim()
                  return (
                    <TableRow key={entry.source_field}>
                      <TableCell className="font-mono text-xs font-medium break-words">
                        {entry.source_field}
                      </TableCell>
                      <TableCell>
                        {suggest.key ? (
                          <span className="block font-mono text-xs font-medium break-words">
                            {suggest.key}
                          </span>
                        ) : null}
                        {suggest.note ? (
                          <span className="text-xs text-muted-foreground">
                            {suggest.note}
                          </span>
                        ) : null}
                      </TableCell>
                      <TableCell className="max-w-sm text-sm text-muted-foreground break-words">
                        {entry.reason || entry.candidate?.description || "—"}
                      </TableCell>
                      <TableCell>
                        <Select
                          value={current}
                          onValueChange={(value) =>
                            setActions((old) => ({
                              ...old,
                              [entry.source_field]: {
                                action: value as RowAction,
                                targetKey: old[entry.source_field]?.targetKey,
                              },
                            }))
                          }
                        >
                          <SelectTrigger
                            className="w-40"
                            aria-label={`Quyết định cho ${entry.source_field}`}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem
                              value="approve"
                              disabled={entry.decision === "AMBIGUOUS"}
                            >
                              Approve
                            </SelectItem>
                            <SelectItem value="change">Change…</SelectItem>
                            <SelectItem value="ignore">Ignore</SelectItem>
                          </SelectContent>
                        </Select>
                        {current === "change" ? (
                          <div className="mt-2">
                            <Input
                              placeholder="target_key — vd: occurred_at"
                              value={override?.targetKey ?? ""}
                              aria-invalid={typedKey === ""}
                              onChange={(event) =>
                                setActions((old) => ({
                                  ...old,
                                  [entry.source_field]: {
                                    action: "change",
                                    targetKey: event.target.value,
                                  },
                                }))
                              }
                            />
                            {typedKey !== "" && !knownKeys.has(typedKey) ? (
                              <p className="mt-1 text-xs text-muted-foreground">
                                Sẽ tạo product field mới “{humanizeKey(typedKey)}
                                ”.
                              </p>
                            ) : null}
                          </div>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Alert>
        <AlertTitle>G1 — Confirm what these columns mean</AlertTitle>
        <AlertDescription>
          Resolve ambiguous mappings and missing required fields before
          importing.
          {changed.length > 0
            ? ` ${changed.length} column(s) changed from the AI proposal.`
            : " The AI proposal is accepted as shown."}
          {pendingChanges.length > 0
            ? ` ${pendingChanges.length} cột đang Change nhưng chưa nhập target_key.`
            : ""}
        </AlertDescription>
      </Alert>

      <div className="flex items-center justify-between">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft data-icon="inline-start" />
            Back to preview
          </Button>
        ) : (
          <span />
        )}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              disabled={
                decide.isPending ||
                mappings.length === 0 ||
                pendingChanges.length > 0
              }
            >
              Confirm mapping &amp; import
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                G1 — Confirm mapping &amp; import?
              </AlertDialogTitle>
              <AlertDialogDescription>
                Import runs in the background and writes sanitized feedback
                only. Analysis never starts automatically.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Check again</AlertDialogCancel>
              <AlertDialogAction onClick={submit}>
                Confirm &amp; import
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- Step 4: Result

export function StepResult({ importId }: { importId: string }) {
  const detail = useImport(importId)
  const item = detail.data
  if (!item) return <Spinner />

  if (item.status === "importing") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Importing…</CardTitle>
          {/* No honest % exists server-side yet — spin instead of faking progress. */}
          <CardDescription>
            You can leave this screen. Reopen the task from Current tasks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Sanitizing rows and storing them…
          </p>
        </CardContent>
      </Card>
    )
  }

  if (item.status === "failed") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardContent className="gap-4">
          <Alert variant="destructive">
            <TriangleAlert className="size-4" />
            <AlertTitle>Import failed</AlertTitle>
            <AlertDescription>{item.error ?? "Unknown error"}</AlertDescription>
          </Alert>
          <Button variant="outline" asChild className="self-start">
            <Link href="/importer">Import another file</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (item.status === "cancelled") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Import cancelled</CardTitle>
          <CardDescription>
            Nothing was written. Start over whenever you are ready.
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <Button variant="outline" asChild>
            <Link href="/importer">Import another file</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  // Defense-in-depth: only a genuinely imported import may show the summary —
  // a pre-import status (mapping_review / profile_ready) landing here must
  // never render a phantom "0 imported" card.
  if (item.status !== "imported") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Import still in review</CardTitle>
          <CardDescription>
            This import has not run yet — confirm its column mapping first.
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <Button variant="outline" asChild>
            <Link href="/importer">Back to the Importer</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  const report = item.report
  return (
    <section className="mx-auto flex max-w-xl flex-col gap-6 py-10">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="size-5 text-lichen" />
        <h2 className="font-heading text-xl">Import completed</h2>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <Card size="sm">
          <CardContent className="items-center gap-1">
            <span className="font-mono text-2xl font-semibold">
              {item.source_row_count ?? item.row_count ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">source rows</span>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="items-center gap-1">
            <span className="font-mono text-2xl font-semibold text-lichen">
              {report?.imported ?? item.row_count ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">imported</span>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="items-center gap-1">
            <span
              className={`font-mono text-2xl font-semibold ${
                (report?.failed ?? 0) > 0 ? "text-destructive" : ""
              }`}
            >
              {report?.failed ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">failed</span>
          </CardContent>
        </Card>
      </div>
      {report && report.errors.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Row errors</CardTitle>
          </CardHeader>
          <CardContent className="gap-2">
            <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
              {report.errors.slice(0, 10).map((e, i) => (
                <li
                  key={`${e.row}-${i}`}
                  className="font-mono text-xs break-words"
                >
                  Row {e.row}: {e.reason}
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">
              Correct and re-import only the failed rows.
            </p>
          </CardContent>
        </Card>
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
  )
}

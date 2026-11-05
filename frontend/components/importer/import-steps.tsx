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
import { useT } from "@/lib/i18n"
import { readableError } from "@/lib/evidence"

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
  embedded = false,
}: {
  productReady: boolean
  onUploaded: (importId: string) => void
  onCancel: () => void
  /** Nhúng thẳng trên màn Importer: không khung căn giữa, không nút Huỷ. */
  embedded?: boolean
}) {
  const t = useT().importer
  const createImport = useCreateImport()
  const [file, setFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { productId, loading } = useProduct()

  // Chọn hoặc thả file là tải lên ngay — không cần thêm một nút xác nhận.
  const upload = async (picked: File | null) => {
    setFile(picked)
    if (!picked || !productId || createImport.isPending) return
    try {
      const created = await createImport.mutateAsync({ file: picked, productId })
      toast.success(t.file.uploaded)
      onUploaded(created.id)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : t.file.uploadFailed)
    }
  }

  return (
    <section
      className={
        embedded ? "flex flex-col" : "mx-auto flex max-w-xl flex-col gap-6 py-10"
      }
    >
      <Card>
        <CardHeader>
          <CardTitle>{t.file.title}</CardTitle>
          <CardDescription>{t.file.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-border p-8 text-center transition-colors hover:border-signal/60"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const dropped = e.dataTransfer.files?.[0]
              if (dropped && productReady) void upload(dropped)
            }}
          >
            {createImport.isPending && file ? (
              <p className="flex items-center gap-2 text-sm font-medium" role="status">
                <Spinner /> {t.file.uploading(file.name)}
              </p>
            ) : (
              <>
                <Upload className="size-8 text-muted-foreground" />
                <p className="text-sm">{t.file.drop}</p>
                <p className="text-xs text-muted-foreground">{t.file.or}</p>
                <Button
                  disabled={!productReady}
                  onClick={() => inputRef.current?.click()}
                >
                  <FileSpreadsheet data-icon="inline-start" />
                  {t.file.choose}
                </Button>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => {
                void upload(e.target.files?.[0] ?? null)
                e.target.value = ""
              }}
            />
            {!productReady && !loading ? (
              <p className="text-sm text-destructive">{t.file.needProduct}</p>
            ) : null}
          </div>
          <p className="mt-4 text-sm text-muted-foreground">{t.file.errorsHint}</p>
        </CardContent>
        {embedded ? null : (
          <CardFooter>
            <Button variant="ghost" onClick={onCancel} disabled={createImport.isPending}>
              {t.file.cancel}
            </Button>
          </CardFooter>
        )}
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
  const t = useT().importer
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
          <AlertTitle className="flex items-center gap-2">
            <Spinner /> {t.preview.proposing}
          </AlertTitle>
          <AlertDescription>{t.preview.proposingBody}</AlertDescription>
        </Alert>
      ) : null}
      {detail.data?.error ? (
        <Alert variant="destructive">
          <TriangleAlert className="size-4" />
          <AlertTitle>{t.preview.lastFailed}</AlertTitle>
          <AlertDescription>{readableError(detail.data.error)}</AlertDescription>
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
          <AlertTitle>{t.preview.loadFailed}</AlertTitle>
          <AlertDescription>
            {preview.error.message} — {t.preview.loadFailedHint}
          </AlertDescription>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 w-fit"
            onClick={() => void preview.refetch()}
          >
            {t.preview.retry}
          </Button>
        </Alert>
      ) : preview.data ? (
        <Card>
          <CardHeader>
            <CardTitle>{preview.data.original_filename ?? "CSV"}</CardTitle>
            <CardDescription className="font-mono text-xs">
              {t.preview.rowsCols(
                preview.data.source_row_count,
                preview.data.column_profiles.length
              )}
            </CardDescription>
            <CardAction>
              <Badge variant="outline">{t.preview.noAi}</Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.preview.colColumn}</TableHead>
                  <TableHead>{t.preview.colType}</TableHead>
                  <TableHead>{t.preview.colSample}</TableHead>
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
            <p className="text-xs text-muted-foreground">{t.preview.hint}</p>
          </CardFooter>
        </Card>
      ) : null}
      <div className="flex items-center justify-between">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft data-icon="inline-start" />
            {t.preview.backToFile}
          </Button>
        ) : (
          <span />
        )}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              disabled={
                !preview.data ||
                propose.isPending ||
                detail.data?.status === "mapping_generating"
              }
            >
              {propose.isPending ? <Spinner data-icon="inline-start" /> : null}
              {t.preview.suggest}
              <ArrowRight data-icon="inline-end" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t.preview.confirmTitle}</AlertDialogTitle>
              <AlertDialogDescription>{t.preview.confirmBody}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t.preview.confirmBack}</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  propose.mutate(importId, {
                    ...(onProposed ? { onSuccess: onProposed } : {}),
                    onError: (err) =>
                      toast.error(
                        err instanceof ApiError
                          ? err.message
                          : t.preview.startFailed
                      ),
                  })
                }
              >
                {t.preview.confirmGo}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- Step 3: Mapping (G1)

/** Quyết định người dùng trên mỗi hàng — "change" được dịch thành remap
 * (key đã có trong schema) hoặc promote (field mới) lúc submit. */
type RowAction = "approve" | "change" | "ignore"

function suggestView(
  entry: MappingItem,
  t: ReturnType<typeof useT>["importer"]["mapping"]
): { key: string | null; note: string } {
  if (entry.decision === "AMBIGUOUS") return { key: null, note: t.ambiguous }
  if (entry.target) return { key: entry.target, note: t.core[entry.target] ?? "" }
  if (entry.candidate) return { key: entry.candidate.key, note: t.newField }
  if (entry.decision === "SOURCE_META") return { key: null, note: t.sourceMeta }
  return { key: null, note: t.ignore }
}

/** Đích mà đề xuất AI gán cho một cột (MAP/PROMOTE), null nếu không ghi vào field. */
function proposedTarget(entry: MappingItem): string | null {
  if (entry.decision === "MAP") return entry.target
  if (entry.decision === "PROMOTE") return entry.candidate?.key ?? null
  return null
}

const TEXT_COLUMN = /content|text|body|comment|review|feedback|message|noi.?dung/i

/** Mỗi đích chỉ nhận một cột (server trả 422 nếu trùng). Khi AI đề xuất trùng,
 * giữ cột tin cậy nhất (hoà thì ưu tiên tên kiểu "content") và mặc định bỏ qua
 * các cột còn lại — trả về map cột bị bỏ → cột được giữ. */
export function autoIgnoredDuplicates(
  mappings: MappingItem[]
): Map<string, string> {
  const byTarget = new Map<string, MappingItem[]>()
  for (const entry of mappings) {
    const key = proposedTarget(entry)
    if (key) byTarget.set(key, [...(byTarget.get(key) ?? []), entry])
  }
  const ignored = new Map<string, string>()
  for (const group of byTarget.values()) {
    if (group.length < 2) continue
    const [keep, ...rest] = [...group].sort(
      (a, b) =>
        b.confidence - a.confidence ||
        Number(TEXT_COLUMN.test(b.source_field)) -
          Number(TEXT_COLUMN.test(a.source_field))
    )
    for (const entry of rest) ignored.set(entry.source_field, keep.source_field)
  }
  return ignored
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
  const { mapping: t, preview: previewCopy } = useT().importer
  const proposingLabel = previewCopy.proposing
  const mapping = useGetMapping(importId)
  const decide = useDecideMapping()
  const { productId } = useProduct()
  const schema = useActiveSchema(productId)
  const [actions, setActions] = useState<
    Record<string, { action: RowAction; targetKey?: string }>
  >({})
  const mappings = useMemo(() => mapping.data?.mappings ?? [], [mapping.data])
  const knownKeys = useMemo(() => {
    const core = schema.data?.core_fields.map((f) => f.key) ?? []
    const fields = schema.data?.schema?.definition.fields.map((f) => f.key) ?? []
    return new Set([...core, ...fields])
  }, [schema.data])

  const autoIgnored = useMemo(() => autoIgnoredDuplicates(mappings), [mappings])
  const defaultAction = (entry: MappingItem): RowAction =>
    entry.decision === "AMBIGUOUS" || autoIgnored.has(entry.source_field)
      ? "ignore"
      : "approve"

  // Đích thực tế theo quyết định hiện tại — phát hiện trùng ngay trên giao diện.
  const owners = new Map<string, string[]>()
  for (const entry of mappings) {
    const override = actions[entry.source_field]
    const action = override?.action ?? defaultAction(entry)
    const key =
      action === "approve"
        ? proposedTarget(entry)
        : action === "change"
          ? (override?.targetKey ?? "").trim() || null
          : null
    if (key) owners.set(key, [...(owners.get(key) ?? []), entry.source_field])
  }
  const conflictWith = (field: string): string | null => {
    for (const fields of owners.values()) {
      if (fields.length > 1 && fields.includes(field))
        return fields.find((f) => f !== field) ?? null
    }
    return null
  }
  const conflictCount = [...owners.values()]
    .filter((fields) => fields.length > 1)
    .reduce((n, fields) => n + fields.length, 0)

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
            err instanceof ApiError ? err.message : t.importFailed
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
                <TableHead className="w-40">{t.colCsv}</TableHead>
                <TableHead className="w-44">{t.colSuggest}</TableHead>
                <TableHead>{t.colExplain}</TableHead>
                <TableHead className="w-56">{t.colAction}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mapping.isPending ? (
                <TableRow>
                  <TableCell colSpan={4}>
                    <p className="flex items-center gap-2 py-4 text-sm text-muted-foreground" role="status">
                      <Spinner /> {proposingLabel}
                    </p>
                  </TableCell>
                </TableRow>
              ) : (
                mappings.map((entry) => {
                  const override = actions[entry.source_field]
                  const current = override?.action ?? defaultAction(entry)
                  const suggest = suggestView(entry, t)
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
                            aria-label={t.decisionFor(entry.source_field)}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem
                              value="approve"
                              disabled={entry.decision === "AMBIGUOUS"}
                            >
                              {t.approve}
                            </SelectItem>
                            <SelectItem value="change">{t.change}</SelectItem>
                            <SelectItem value="ignore">{t.ignore}</SelectItem>
                          </SelectContent>
                        </Select>
                        {current === "ignore" &&
                        autoIgnored.has(entry.source_field) ? (
                          <p className="mt-1 max-w-48 text-xs text-muted-foreground">
                            {t.duplicateAuto(autoIgnored.get(entry.source_field) ?? "")}
                          </p>
                        ) : null}
                        {conflictWith(entry.source_field) ? (
                          <p className="mt-1 max-w-48 text-xs text-destructive" role="alert">
                            {t.duplicateConflict(conflictWith(entry.source_field) ?? "")}
                          </p>
                        ) : null}
                        {current === "change" ? (
                          <div className="mt-2">
                            <Input
                              placeholder={t.targetPlaceholder}
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
                                {t.willCreate(humanizeKey(typedKey))}
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
        <AlertTitle>{t.gateTitle}</AlertTitle>
        <AlertDescription>
          {t.gateBody}
          {changed.length > 0 ? t.changed(changed.length) : ""}
          {pendingChanges.length > 0 ? t.pendingChange(pendingChanges.length) : ""}
          {conflictCount > 0 ? t.conflicts(conflictCount) : ""}
        </AlertDescription>
      </Alert>

      <div className="flex items-center justify-between">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft data-icon="inline-start" />
            {t.backToPreview}
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
                pendingChanges.length > 0 ||
                conflictCount > 0
              }
            >
              {decide.isPending ? <Spinner data-icon="inline-start" /> : null}
              {t.confirm}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t.confirmTitle}</AlertDialogTitle>
              <AlertDialogDescription>{t.confirmBody}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t.checkAgain}</AlertDialogCancel>
              <AlertDialogAction onClick={submit}>{t.go}</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- Step 4: Result

export function StepResult({ importId }: { importId: string }) {
  const t = useT().importer.result
  const detail = useImport(importId)
  const item = detail.data
  if (!item) return <Spinner />

  if (item.status === "importing") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>{t.importing}</CardTitle>
          {/* No honest % exists server-side yet — spin instead of faking progress. */}
          <CardDescription>{t.importingBody}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> {t.importingStatus}
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
            <AlertTitle>{t.failed}</AlertTitle>
            <AlertDescription>{item.error ? readableError(item.error) : t.unknownError}</AlertDescription>
          </Alert>
          <Button variant="outline" asChild className="self-start">
            <Link href="/importer?new=1">{t.another}</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (item.status === "cancelled") {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>{t.cancelled}</CardTitle>
          <CardDescription>{t.cancelledBody}</CardDescription>
        </CardHeader>
        <CardFooter>
          <Button variant="outline" asChild>
            <Link href="/importer?new=1">{t.another}</Link>
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
          <CardTitle>{t.inReview}</CardTitle>
          <CardDescription>{t.inReviewBody}</CardDescription>
        </CardHeader>
        <CardFooter>
          <Button variant="outline" asChild>
            <Link href="/importer">{t.backToImporter}</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  const report = item.report
  const importedRows = report?.imported ?? item.row_count ?? 0
  return (
    <section className="mx-auto flex max-w-xl flex-col gap-6 py-10">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="size-5 text-lichen" />
        <h2 className="font-heading text-xl">{t.done}</h2>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <Card size="sm">
          <CardContent className="items-center gap-1">
            <span className="font-mono text-2xl font-semibold">
              {item.source_row_count ?? item.row_count ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">{t.sourceRows}</span>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="items-center gap-1">
            <span className="font-mono text-2xl font-semibold text-lichen">
              {importedRows}
            </span>
            <span className="text-xs text-muted-foreground">{t.imported}</span>
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
            <span className="text-xs text-muted-foreground">{t.failedRows}</span>
          </CardContent>
        </Card>
      </div>
      {report && report.errors.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t.rowErrors}</CardTitle>
          </CardHeader>
          <CardContent className="gap-2">
            <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
              {report.errors.slice(0, 10).map((e, i) => (
                <li
                  key={`${e.row}-${i}`}
                  className="font-mono text-xs break-words"
                >
                  {t.rowError(e.row, e.reason)}
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">{t.rowErrorsHint}</p>
          </CardContent>
        </Card>
      ) : null}
      {importedRows > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t.nextTitle}</CardTitle>
            <CardDescription>{t.nextBody}</CardDescription>
          </CardHeader>
          <CardFooter className="justify-between gap-2">
            <Button variant="ghost" asChild>
              <Link href="/importer?new=1">{t.another}</Link>
            </Button>
            <Button asChild size="lg">
              <Link href={`/vault?import=${importId}&analyze=1`}>
                {t.classify}
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          </CardFooter>
        </Card>
      ) : (
        <Button variant="outline" asChild className="self-start">
          <Link href="/importer?new=1">{t.another}</Link>
        </Button>
      )}
    </section>
  )
}

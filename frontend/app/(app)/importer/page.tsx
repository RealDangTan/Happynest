"use client"
import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, FileSpreadsheet } from "lucide-react"
import {
  Badge,
} from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { apiFetch } from "@/lib/api"
import { useT } from "@/lib/i18n"
import type { ImportListResponse } from "@/lib/types"
import { useImport } from "@/hooks/use-imports"
import { useProduct } from "@/hooks/use-product"
import { NextStepBar } from "@/components/journey/next-step-bar"
import { PageHeader } from "@/components/page-header"
import { Stepper } from "@/components/stepper"
import {
  IMPORT_STEPS,
  PHASE_STEP,
  StepFile,
  StepMapping,
  StepPreview,
  StepResult,
  phaseForImport,
  type Phase,
} from "@/components/importer/import-steps"

const STATUS_TONE: Record<
  string,
  "secondary" | "default" | "destructive" | "outline"
> = {
  profile_ready: "default",
  mapping_generating: "secondary",
  mapping_review: "default",
  importing: "secondary",
  imported: "outline",
  failed: "destructive",
  cancelled: "outline",
}

function StatusBadge({ status }: { status: string }) {
  const t = useT().importer
  return (
    <Badge variant={STATUS_TONE[status] ?? "secondary"}>
      {t.status[status] ?? status}
    </Badge>
  )
}

function useProductImports(productId: string | null) {
  return useQuery({
    queryKey: ["imports", "product", productId],
    queryFn: () =>
      apiFetch<ImportListResponse>(
        `/api/imports?limit=50&product_id=${productId}`
      ),
    enabled: productId != null,
    refetchInterval: 5000,
    staleTime: 0,
  })
}

// ---------------------------------------------------------------- S01 screen

export default function ImporterPage() {
  const t = useT().importer
  const { product, productId } = useProduct()
  const imports = useProductImports(productId)
  const router = useRouter()
  const searchParams = useSearchParams()
  const resumeId = searchParams.get("import")
  const startNew = searchParams.get("new") === "1"
  const [phase, setPhase] = useState<Phase>("idle")
  const [importId, setImportId] = useState<string | null>(null)
  const wizardImport = useImport(importId)

  // Deep-link từ Activity Center / lộ trình (/importer?import=<id>): mở wizard
  // tại bước khớp trạng thái server; ?new=1 mở thẳng bước chọn file. Áp intent
  // ngay trong render (không qua effect), rồi gỡ param để refresh không kéo lại.
  const intent = resumeId ? `import:${resumeId}` : startNew ? "new" : null
  const [appliedIntent, setAppliedIntent] = useState<string | null>(null)
  if (intent !== appliedIntent) {
    setAppliedIntent(intent)
    if (resumeId) {
      setImportId(resumeId)
      setPhase("preview")
    } else if (startNew) {
      setImportId(null)
      setPhase("file")
    }
  }
  useEffect(() => {
    if (intent) router.replace("/importer", { scroll: false })
  }, [intent, router])

  // Proposal accepted → the mapping review (G1) replaces the preview step.
  // Phase luôn được đối chiếu với trạng thái server để một task mở lại từ
  // Current tasks / deep-link không bao giờ rơi vào bước sai.
  const status = wizardImport.data?.status
  const effectivePhase: Phase =
    !wizardImport.data || phase === "idle" || phase === "file"
      ? phase
      : status === "mapping_generating" && phase !== "preview"
        ? phase
        : phaseForImport(wizardImport.data)

  const waiting = useMemo(() => {
    const items = imports.data?.items ?? []
    return items.filter((i) =>
      [
        "profile_ready",
        "mapping_generating",
        "mapping_review",
        "failed",
      ].includes(i.status)
    )
  }, [imports.data])

  const history = useMemo(() => {
    const items = imports.data?.items ?? []
    return items.filter((i) => ["imported", "cancelled"].includes(i.status))
  }, [imports.data])

  // "file" phase has no importId yet — it is set by the upload callback before
  // preview/mapping/result, which always run with a valid importId.
  if (effectivePhase !== "idle" && (effectivePhase === "file" || importId)) {
    const stepIndex = IMPORT_STEPS.indexOf(PHASE_STEP[effectivePhase])
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button variant="ghost" size="sm" onClick={() => setPhase("idle")}>
            <ArrowLeft data-icon="inline-start" />
            {t.back}
          </Button>
          <Stepper
            steps={t.steps}
            current={t.steps[stepIndex]}
            label={t.stepsLabel}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {t.productLine(product?.name ?? "…")}
        </p>
        {effectivePhase === "file" ? (
          <StepFile
            productReady={Boolean(productId)}
            onUploaded={(id) => {
              setImportId(id)
              setPhase("preview")
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
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <NextStepBar />

      <PageHeader title={t.title} description={t.description} />

      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="flex min-w-0 flex-col gap-8">
          <StepFile
            productReady={Boolean(productId)}
            onUploaded={(id) => {
              setImportId(id)
              setPhase("preview")
            }}
            onCancel={() => setPhase("idle")}
            embedded
          />

          {waiting.length ? (
            <Card>
              <CardHeader>
                <CardTitle>{t.queueTitle}</CardTitle>
                <CardDescription>{t.queueDescription}</CardDescription>
              </CardHeader>
              <CardContent className="gap-2">
                {waiting.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 rounded-lg bg-secondary/30 px-4 py-3"
                  >
                    <FileSpreadsheet className="size-4 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {item.original_filename ?? item.id}
                      </p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {item.source_row_count ?? item.row_count ?? 0}
                      </p>
                    </div>
                    <StatusBadge status={item.status} />
                    <Button
                      size="sm"
                      onClick={() => {
                        setImportId(item.id)
                        setPhase("preview")
                      }}
                    >
                      {t.continue}
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {history.length ? (
            <Card>
              <CardHeader>
                <CardTitle>{t.historyTitle}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t.colFile}</TableHead>
                      <TableHead>{t.colRows}</TableHead>
                      <TableHead>{t.colStatus}</TableHead>
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
                          <Button size="sm" variant="ghost" asChild>
                            <Link href={`/vault?import=${item.id}`}>{t.open}</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : null}
        </div>

        <Card size="sm" className="self-start">
          <CardHeader>
            <CardTitle>{t.howTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed">
              {t.how.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

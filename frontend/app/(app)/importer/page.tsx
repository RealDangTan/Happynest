"use client"
import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, ArrowRight, FileSpreadsheet, Inbox } from "lucide-react"
import {
  Badge,
} from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { apiFetch } from "@/lib/api"
import type { ImportListResponse } from "@/lib/types"
import { useImport } from "@/hooks/use-imports"
import { useProduct } from "@/hooks/use-product"
import { FirstRunGuide } from "@/components/onboarding/first-run-guide"
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

const SOURCE_TILES = ["Survey app", "App store", "Support inbox", "NPS tool"]

const STATUS_BADGE: Record<
  string,
  { label: string; tone: "secondary" | "default" | "destructive" | "outline" }
> = {
  profile_ready: { label: "Needs mapping review", tone: "default" },
  mapping_generating: { label: "Proposing mapping", tone: "secondary" },
  mapping_review: { label: "Needs mapping review", tone: "default" },
  importing: { label: "Importing", tone: "secondary" },
  imported: { label: "Imported", tone: "outline" },
  failed: { label: "Failed", tone: "destructive" },
  cancelled: { label: "Cancelled", tone: "outline" },
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_BADGE[status] ?? {
    label: status,
    tone: "secondary" as const,
  }
  return <Badge variant={s.tone}>{s.label}</Badge>
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
  const { product, productId } = useProduct()
  const imports = useProductImports(productId)
  const router = useRouter()
  const searchParams = useSearchParams()
  const resumeId = searchParams.get("import")
  const [phase, setPhase] = useState<Phase>("idle")
  const [importId, setImportId] = useState<string | null>(null)
  const wizardImport = useImport(importId)

  // Deep-link từ Activity Center (/importer?import=<id>): mở wizard tại bước
  // khớp trạng thái server rồi gỡ param để refresh không bị kéo lại wizard.
  useEffect(() => {
    if (!resumeId) return
    setImportId(resumeId)
    setPhase("preview")
    router.replace("/importer", { scroll: false })
  }, [resumeId, router])

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

  const recent = useMemo(() => {
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
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={() => setPhase("idle")}>
            <ArrowLeft data-icon="inline-start" />
            Importer
          </Button>
          <Stepper
            steps={IMPORT_STEPS}
            current={PHASE_STEP[effectivePhase]}
            label="Import steps"
          />
        </div>
        <p className="text-sm text-muted-foreground">
          Product: {product?.name ?? "…"}
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
        <div className="flex min-w-0 flex-col gap-8">
          <Card>
            <CardContent className="items-center gap-6 py-10 text-center">
              <Button
                size="lg"
                onClick={() => setPhase("file")}
                disabled={!productId}
              >
                <Inbox data-icon="inline-start" />
                Import CSV
              </Button>
              <div className="mx-auto grid max-w-md grid-cols-2 gap-3">
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
              <p className="text-xs text-muted-foreground">
                CSV is the supported source. Additional sources are
                placeholders.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Current tasks — imports</CardTitle>
              <CardDescription>
                Các lô đang chờ duyệt mapping hoặc gặp lỗi.
              </CardDescription>
            </CardHeader>
            {recent.length ? (
              <CardContent className="gap-2">
                {recent.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 rounded-lg bg-secondary/30 px-4 py-3"
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
                        setImportId(item.id)
                        setPhase("preview")
                      }}
                    >
                      Continue mapping
                    </Button>
                  </div>
                ))}
              </CardContent>
            ) : (
              <CardContent>
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No imports waiting</EmptyTitle>
                    <EmptyDescription>
                      Import a CSV to get started.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent imports</CardTitle>
            </CardHeader>
            {history.length ? (
              <CardContent className="p-0">
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
              </CardContent>
            ) : (
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  No completed imports yet.
                </p>
              </CardContent>
            )}
          </Card>
        </div>

        <Card size="sm" className="self-start">
          <CardHeader>
            <CardTitle>How it works</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed">
              <li>1. Upload a CSV — preview stays sanitized, no AI yet.</li>
              <li>2. AI proposes column meanings.</li>
              <li>
                <strong>G1</strong> — you confirm the mapping before anything
                imports.
              </li>
              <li>3. Import runs; row errors are reported per row.</li>
              <li>4. Continue in the Feedback Vault.</li>
            </ol>
          </CardContent>
          {history.length ? (
            <CardFooter>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/vault">
                  Open Feedback Vault
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardFooter>
          ) : null}
        </Card>
      </div>
    </div>
  )
}

"use client";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileSpreadsheet,
  PlayCircle,
  Plus,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useImports } from "@/hooks/use-imports";
import { useInsights } from "@/hooks/use-insights";
import { useProduct } from "@/hooks/use-product";
import { useCreateProduct } from "@/hooks/use-products";
import { ApiError } from "@/lib/api";

const DISMISS_KEY = "happynest.first-run-guide.dismissed";

/**
 * First-run checklist for a brand-new workspace. Steps check off from real
 * backend state (product exists → CSV imported → first insight), never from
 * local progress — so the guide can't lie. Hidden once any insight exists or
 * the user dismisses it.
 */
export function FirstRunGuide({ onStartImport }: { onStartImport?: () => void }) {
  const { products, loading } = useProduct();
  const imports = useImports();
  const insights = useInsights();

  // Same pattern as ProductProvider's saved choice: read localStorage lazily.
  // During hydration the products query is still pending, so the guide renders
  // null either way — the localStorage result only matters post-hydration.
  const [dismissed, setDismissed] = useState(
    () =>
      typeof window !== "undefined" &&
      localStorage.getItem(DISMISS_KEY) === "1",
  );

  const hasProduct = products.length > 0;
  const importedCount = (imports.data?.items ?? []).filter(
    (i) => i.status === "imported",
  ).length;
  const hasImported = importedCount > 0;
  const hasInsight = (insights.data?.items ?? []).length > 0;

  // `loading` doubles as the hydration gate: queries have no data on the
  // server, so the guide never renders during SSR.
  if (loading || dismissed || hasInsight) return null;

  const doneCount = [hasProduct, hasImported, hasInsight].filter(Boolean).length;

  return (
    <section aria-label="Getting started" className="rounded-xl border bg-card">
      <header className="flex items-center justify-between gap-3 border-b px-5 py-4">
        <div className="flex items-baseline gap-3">
          <h2 className="font-heading text-lg">Set up your workspace</h2>
          <p
            className="font-mono text-xs text-muted-foreground"
            aria-live="polite"
          >
            {doneCount}/3
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            localStorage.setItem(DISMISS_KEY, "1");
            setDismissed(true);
          }}
        >
          <X data-icon="inline-start" />
          Hide this guide
        </Button>
      </header>

      <ol className="divide-y">
        <Step
          index="01"
          stage="LISTEN"
          title="Create your product"
          description="The workspace organizes everything under one product — its AI feature, its users, its feedback."
          done={hasProduct}
          doneLabel={products[0]?.name}
        >
          <CreateProductAction />
        </Step>
        <Step
          index="02"
          stage="LISTEN"
          title="Import your first CSV"
          description="One column is required: the feedback text. Dates and sources are mapped by AI, and you confirm before anything is stored."
          done={hasImported}
          doneLabel={
            hasImported ? `${importedCount} import(s) completed` : undefined
          }
        >
          {onStartImport ? (
            <Button size="sm" disabled={!hasProduct} onClick={onStartImport}>
              <FileSpreadsheet data-icon="inline-start" />
              Import CSV
            </Button>
          ) : (
            <Button size="sm" asChild disabled={!hasProduct}>
              <Link href="/importer">
                <FileSpreadsheet data-icon="inline-start" />
                Go to Importer
              </Link>
            </Button>
          )}
        </Step>

        <Step
          index="03"
          stage="UNDERSTAND"
          title="Run your first analysis"
          description="The agent clusters feedback, finds problems, and proposes insights. You review every insight before it counts."
          done={hasInsight}
          doneLabel="First insights are in"
        >
          <Button size="sm" variant="outline" asChild disabled={!hasImported}>
            <Link href="/analysis">
              <PlayCircle data-icon="inline-start" />
              Run analysis
            </Link>
          </Button>
        </Step>
      </ol>

      {doneCount === 3 ? (
        <footer className="flex items-center justify-between border-t px-4 py-3 text-sm">
          <span className="flex items-center gap-2 text-lichen">
            <Check className="size-4" /> Workspace ready — the journey continues in
            Reports.
          </span>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/reports/summary">
              Open Reports
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        </footer>
      ) : null}
    </section>
  );
}

function Step({
  index,
  stage,
  title,
  description,
  done,
  doneLabel,
  children,
}: {
  index: string;
  stage: string;
  title: string;
  description: string;
  done: boolean;
  doneLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <li className="flex gap-4 px-5 py-5">
      <div className="flex flex-col items-center pt-0.5">
        <span
          aria-hidden
          className={
            done
              ? "flex size-8 items-center justify-center rounded-full bg-lichen/15 text-lichen"
              : "flex size-8 items-center justify-center rounded-full border bg-secondary/50 font-mono text-xs text-muted-foreground"
          }
        >
          {done ? <Check className="size-4" /> : index}
        </span>
      </div>
      <div className="min-w-0 flex-1 space-y-0.5">
        <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          {stage}
        </p>
        <h3
          className={
            done
              ? "text-sm font-medium text-muted-foreground line-through"
              : "text-sm font-medium"
          }
        >
          {title}
        </h3>
        <p className="mt-0.5 max-w-prose text-sm text-muted-foreground">
          {description}
        </p>
      </div>
      <div className="flex shrink-0 items-center">
        {done ? (
          <span className="max-w-40 truncate text-sm text-lichen">
            {doneLabel ?? "Done"}
          </span>
        ) : (
          children
        )}
      </div>
    </li>
  );
}

/** Step 1 action — same contract as the navbar's Create product dialog. */
function CreateProductAction() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const { createProduct } = useProduct();
  const createProductMutation = useCreateProduct();

  const handleCreate = async () => {
    if (name.trim().length < 2) return;
    try {
      await createProduct(name.trim(), description.trim() || undefined);
      setOpen(false);
      setName("");
      setDescription("");
      toast.success("Product created — next: import a CSV.");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not create product",
      );
    }
  };

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus data-icon="inline-start" />
        Create product
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create product</DialogTitle>
            <DialogDescription>
              A new product starts empty — the Importer is the first screen.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="guide-product-name">Name</FieldLabel>
              <Input
                id="guide-product-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Demo AI"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="guide-product-description">
                Description
              </FieldLabel>
              <Input
                id="guide-product-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this product does (optional)"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleCreate()}
              disabled={name.trim().length < 2 || createProductMutation.isPending}
            >
              {createProductMutation.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : null}
              Create product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

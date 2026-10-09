"use client";
import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { AiBadge } from "@/components/ai/ai-badge";
import { PageHeader } from "@/components/page-header";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useInsights } from "@/hooks/use-insights";
import { useActions } from "@/hooks/use-actions";
import { ActionDecisionSupport } from "@/components/actions/action-decision-support";
import { useProduct } from "@/hooks/use-product";
import { DEPARTMENTS, departmentLabel, toDepartment } from "@/lib/departments";
import { effectiveScores } from "@/lib/matrix";
import type { ActionItem } from "@/lib/types";

function priorityLabel(action: ActionItem): string {
  const score = action.priority_score;
  if (score >= 7) return "High";
  if (score >= 4) return "Medium";
  return "Low";
}

const STATUS_TONE: Record<string, "secondary" | "default" | "destructive" | "outline"> = {
  accepted: "secondary",
  proposed: "default",
  edited: "outline",
  rejected: "destructive",
};

function Stakeholders({ initialReportId }: { initialReportId: string | null }) {
  const { product } = useProduct();
  const insights = useInsights();
  const [reportId, setReportId] = useState<string | null>(initialReportId);
  const [statusFilter, setStatusFilter] = useState("accepted");
  const [department, setDepartment] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const eligibleReports = useMemo(
    () => (insights.data?.items ?? []).filter((i) => i.status !== "pending"),
    [insights.data],
  );

  // Derived selection: falls back to the first eligible report.
  const effectiveReportId = reportId ?? eligibleReports[0]?.id ?? null;

  const actions = useActions(effectiveReportId);
  const allItems = useMemo(() => actions.data?.items ?? [], [actions.data]);

  const filtered = useMemo(() => {
    return allItems.filter((a) => {
      if (department !== "all" && toDepartment(a.function) !== department) return false;
      // A selected proposed action stays visible even under the Accepted filter.
      const statusVisible =
        a.status === statusFilter ||
        (statusFilter === "accepted" && a.status === "edited" && a.id === selectedId) ||
        (statusFilter === "accepted" && a.status === "proposed" && a.id === selectedId);
      if (!statusVisible) return false;
      if (search && !a.recommendation.toLowerCase().includes(search.toLowerCase()))
        return false;
      return true;
    });
  }, [allItems, department, statusFilter, search, selectedId]);

  const selected = allItems.find((a) => a.id === selectedId) ?? null;

  const departmentCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const a of allItems) {
      const key = toDepartment(a.function);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  }, [allItems]);

  const emptyDepartment = department !== "all" && filtered.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title={product?.name ?? "Stakeholders"}
        description="Gói insight thành bản tin cho từng phòng ban — ai cần biết gì, vì sao."
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select value={effectiveReportId ?? ""} onValueChange={setReportId}>
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Report: choose one" />
          </SelectTrigger>
          <SelectContent>
            {eligibleReports.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                Report: {r.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="accepted">Status: Accepted</SelectItem>
            <SelectItem value="proposed">Status: Proposed</SelectItem>
            <SelectItem value="edited">Status: Edited</SelectItem>
            <SelectItem value="rejected">Status: Rejected</SelectItem>
            <SelectItem value="all">Status: All</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid min-w-0 gap-6 lg:grid-cols-[200px_minmax(0,1fr)_280px]">
        {/* By department */}
        <aside className="space-y-1">
          <h2 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            By department
          </h2>
          {["all", ...DEPARTMENTS.map((d) => d.toLowerCase())].map((key) => (
            <button
              key={key}
              onClick={() => setDepartment(key)}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                department === key ? "bg-accent font-medium" : "hover:bg-accent/60"
              }`}
            >
              {department === key ? <span aria-hidden>›</span> : <span className="w-2" aria-hidden />}
              <span className="flex-1 capitalize">{key}</span>
              {key !== "all" && (departmentCounts.get(key) ?? 0) > 0 ? (
                <span className="font-mono text-xs text-muted-foreground">
                  {departmentCounts.get(key)}
                </span>
              ) : null}
            </button>
          ))}
        </aside>

        {/* Actions table */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Search actions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {actions.isError ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
              Could not load actions — {actions.error.message}
              <Button
                size="sm"
                variant="outline"
                className="mt-2 block"
                onClick={() => void actions.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : actions.isPending ? (
            <Spinner />
          ) : filtered.length === 0 ? (
            <Empty className="border">
              <EmptyHeader>
                <EmptyTitle>
                  {emptyDepartment ? "No actions for this department" : "Nothing here"}
                </EmptyTitle>
                <EmptyDescription>
                  {emptyDepartment
                    ? "Departments without relevant actions can still review proposed work."
                    : "Adjust the filters or check another report."}
                </EmptyDescription>
              </EmptyHeader>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setStatusFilter("proposed")}>
                  Show proposed actions
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/matrix?report=${effectiveReportId ?? ""}`}>Open Priority Matrix</Link>
                </Button>
              </div>
            </Empty>
          ) : (
            <div className="rounded-xl border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Action</TableHead>
                    <TableHead className="w-24">Priority</TableHead>
                    <TableHead className="w-28">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((a) => (
                    <TableRow
                      key={a.id}
                      className={`cursor-pointer ${
                        selectedId === a.id ? "bg-accent" : ""
                      }`}
                      onClick={() => setSelectedId(a.id)}
                    >
                      <TableCell className="min-w-0">
                        <span className="flex items-start gap-2">
                          {selectedId === a.id ? (
                            <span aria-hidden className="mt-0.5">›</span>
                          ) : (
                            <span className="w-2" aria-hidden />
                          )}
                          <span className="min-w-0 text-sm break-words">{a.recommendation}</span>
                        </span>
                        <span className="mt-1 block pl-4 font-mono text-xs text-muted-foreground">
                          {departmentLabel(a.function)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{priorityLabel(a)}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_TONE[a.status] ?? "secondary"}>
                          {a.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* WHAT panel */}
        <aside className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            What
          </h2>
          {selected ? (
            <div className="space-y-4 rounded-xl border bg-card p-4">
              <div>
                <p className="font-mono text-xs text-signal">A-{selected.id.slice(0, 8)}</p>
                <p className="mt-1 font-heading text-base leading-snug">
                  {selected.recommendation}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="outline">{departmentLabel(selected.function)}</Badge>
                  <AiBadge />
                </div>
              </div>
              <div className="space-y-1 text-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Recommendation
                </h3>
                <p>{selected.recommendation}</p>
                {selected.rationale ? (
                  <p className="text-muted-foreground">{selected.rationale}</p>
                ) : null}
              </div>
              <div className="space-y-1 text-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Why
                </h3>
                <p>
                  Finding in{" "}
                  <Link className="text-signal underline" href={`/reports?report=${selected.insight_id}`}>
                    report
                  </Link>{" "}
                  · impact {effectiveScores(selected).impact}, effort{" "}
                  {effectiveScores(selected).effort}
                </p>
              </div>
              <ActionDecisionSupport action={selected} />
              <div className="flex flex-col gap-2">
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/reports?report=${selected.insight_id}`}>Open report</Link>
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/matrix?report=${selected.insight_id}`}>Show in matrix</Link>
                </Button>
              </div>
            </div>
          ) : (
            <p className="rounded-xl border bg-card p-4 text-sm text-muted-foreground">
              Select an action to see what each department should do and the evidence
              behind the decision.
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}

export default function StakeholdersPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <StakeholdersWithParams />
    </Suspense>
  );
}

function StakeholdersWithParams() {
  const params = useSearchParams();
  return <Stakeholders initialReportId={params.get("report")} />;
}

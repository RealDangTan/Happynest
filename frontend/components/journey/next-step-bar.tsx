"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useJourney } from "@/hooks/use-journey";
import { useT, type Dictionary } from "@/lib/i18n";
import { type NextAction, type NextKind } from "@/lib/journey";
import { findStage, STAGE_TONE, TONE_CLASSES } from "@/lib/navigation";
import { cn } from "@/lib/utils";

/** Những bước mà trang đích đọc URL rồi tự làm việc ngay cả khi đang đứng ở đó. */
const INTENT_PARAMS = ["new", "analyze", "ask", "import", "run", "generate", "reclassify"];

function copyFor(next: NextAction, t: Dictionary["journey"]["next"]) {
  const label = next.label ?? "";
  switch (next.kind) {
    case "create-product":
      return t.createProduct;
    case "finish-mapping":
      return { ...t.finishMapping, title: t.finishMapping.title(label) };
    case "importing":
      return { ...t.importing, title: t.importing.title(label) };
    case "import-first":
      return t.importFirst;
    case "classifying":
      return {
        ...t.classifying,
        body: t.classifying.body(next.progress?.done ?? 0, next.progress?.total ?? 0),
      };
    case "build-topics":
      return t.buildTopics;
    case "classify":
      return { ...t.classify, title: t.classify.title(next.count ?? 0) };
    case "reclassify":
      return { ...t.reclassify, title: t.reclassify.title(next.count ?? 0) };
    case "review-finding":
      return { ...t.reviewFinding, body: t.reviewFinding.body(label) };
    case "ask":
      return t.ask;
    case "open-actions":
      return { ...t.openActions, body: t.openActions.body(label) };
    case "generate-actions":
      return { ...t.generateActions, body: t.generateActions.body(label) };
    case "decide-actions":
      return { ...t.decideActions, title: t.decideActions.title(next.count ?? 0) };
    case "handoff":
      return { ...t.handoff, body: t.handoff.body(next.count ?? 0) };
  }
}

/**
 * Dải "bước tiếp theo" (plan 41) đặt đầu mỗi màn của lộ trình: một câu nói việc
 * cần làm + đúng một nút chính. Ẩn nút khi bấm không đổi gì (đã đứng đúng chỗ),
 * để không bao giờ có nút chết. Đứng ở bước cuối → mời bắt đầu vòng mới.
 */
export function NextStepBar({
  className,
  hideKinds = [],
}: {
  className?: string;
  /** Trang tự hiển thị việc này rõ hơn (vd: đang điều tra) — nhường chỗ. */
  hideKinds?: NextKind[];
}) {
  const t = useT();
  const pathname = usePathname();
  const params = useSearchParams();
  const { journey } = useJourney();

  if (!journey) {
    return (
      <div className={cn("flex flex-col gap-3 rounded-xl border bg-card p-4", className)} aria-busy>
        <Skeleton className="h-1.5 w-40" />
        <Skeleton className="h-5 w-72 max-w-full" />
        <span className="sr-only">{t.journey.checking}</span>
      </div>
    );
  }

  const { next } = journey;
  if (hideKinds.includes(next.kind)) return null;
  const target = new URL(next.href, "http://happynest.local");
  const samePage = target.pathname === pathname;
  const complete = next.kind === "handoff" && samePage;
  const copy = complete ? t.journey.next.complete : copyFor(next, t.journey.next);
  const alreadyThere =
    samePage && [...target.searchParams].every(([k, v]) => params.get(k) === v);
  const intentful = [...target.searchParams.keys()].some((k) => INTENT_PARAMS.includes(k));
  const href = complete ? "/importer?new=1" : next.href;
  const showCta = complete || (!alreadyThere && (!samePage || intentful) && !(next.waiting && samePage));

  // Gợi ý mang màu của chặng chứa màn đích (giống sidebar), không đánh số
  // bước — người dùng vẫn đi theo ba chặng tự do.
  const stage = findStage(complete ? "/importer" : target.pathname);
  const tone = TONE_CLASSES[STAGE_TONE[stage.group ?? "listen"]];

  return (
    <section
      aria-label={t.journey.progressLabel}
      className={cn(
        "flex flex-col gap-4 rounded-xl border border-l-4 bg-card p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between sm:p-5",
        tone.border,
        className,
      )}
    >
      <div className="flex min-w-0 flex-col gap-2">
        <p
          className={cn(
            "w-fit rounded-full px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide",
            tone.chip,
          )}
        >
          {t.journey.nextLabel}
          {stage.key ? ` · ${t.nav.items[stage.key]}` : ""}
        </p>
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 className="flex items-center gap-2 font-heading text-lg leading-snug" aria-live="polite">
            {next.waiting && !complete ? <Spinner /> : null}
            <span className="min-w-0 break-words">{copy.title}</span>
          </h2>
          <p className="max-w-prose text-sm text-muted-foreground">{copy.body}</p>
        </div>
        {next.kind === "classifying" && next.progress?.total ? (
          <Progress
            className="max-w-sm"
            value={Math.round((next.progress.done / next.progress.total) * 100)}
            aria-label={copy.title}
          />
        ) : null}
      </div>
      {showCta ? (
        <Button asChild size="lg" variant={next.waiting && !complete ? "outline" : "default"} className="shrink-0 self-start sm:self-center">
          <Link href={href}>
            {copy.cta}
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      ) : null}
    </section>
  );
}

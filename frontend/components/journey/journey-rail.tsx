"use client";
import Link from "next/link";
import { Check } from "lucide-react";
import { useJourney } from "@/hooks/use-journey";
import { useT, type Dictionary } from "@/lib/i18n";
import type { Journey, JourneyStepId } from "@/lib/journey";
import { JOURNEY, LIBRARY } from "@/lib/navigation";
import { cn } from "@/lib/utils";

function stepMeta(
  id: JourneyStepId,
  journey: Journey,
  t: Dictionary["journey"]["meta"],
): string | null {
  const count = journey.steps[id].count ?? 0;
  if (count === 0) return null;
  switch (id) {
    case "import":
      return t.feedback(count);
    case "classify":
      return t.pending(count);
    case "investigate":
      return t.review(count);
    case "act":
      return t.open(count);
    case "handoff":
      return t.accepted(count);
  }
}

/**
 * Sidebar = lộ trình (plan 41): năm bước đánh số nối bằng một sợi chỉ; vòng tròn
 * đổi trạng thái theo dữ liệu thật (xong ✓ / bước kế / chưa tới) và dòng phụ
 * nói còn bao nhiêu việc. Dưới cùng là nhóm "Tra cứu" ngoài luồng chính.
 */
export function JourneyRail({
  pathname,
  collapsed,
  onNavigate,
}: {
  pathname: string;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const t = useT();
  const { journey } = useJourney();

  return (
    <div className="flex w-full flex-col gap-6">
      <div>
        {!collapsed ? (
          <p className="px-2.5 pb-2 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
            {t.journey.title}
          </p>
        ) : null}
        <ol className="flex flex-col" aria-label={t.journey.title}>
          {JOURNEY.map((step, i) => {
            const status = journey?.steps[step.id].status ?? "upcoming";
            const active = pathname === step.href;
            const label = t.nav.items[step.key];
            const meta = journey && !collapsed ? stepMeta(step.id, journey, t.journey.meta) : null;
            const last = i === JOURNEY.length - 1;
            return (
              <li key={step.id} className="relative">
                {!last ? (
                  <span
                    aria-hidden
                    className={cn(
                      "absolute top-8 bottom-[-0.5rem] w-px",
                      collapsed ? "left-1/2" : "left-[1.375rem]",
                      status === "done" ? "bg-lichen/70" : "bg-sidebar-foreground/15",
                    )}
                  />
                ) : null}
                <Link
                  href={step.href}
                  onClick={onNavigate}
                  title={collapsed ? label : undefined}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative flex items-start gap-3 rounded-md px-2.5 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                    collapsed && "justify-center px-0",
                    active
                      ? "bg-sidebar-accent text-sidebar-foreground"
                      : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-semibold",
                      status === "done" && "bg-lichen text-sidebar",
                      status === "current" &&
                        "bg-sidebar-primary text-sidebar-primary-foreground ring-4 ring-lichen/30",
                      status === "upcoming" &&
                        "border border-sidebar-foreground/25 bg-sidebar text-sidebar-foreground/60",
                    )}
                  >
                    {status === "done" ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
                  </span>
                  {!collapsed ? (
                    <span className="flex min-w-0 flex-col pt-0.5">
                      <span className={cn("truncate leading-5", (active || status === "current") && "font-medium")}>
                        {label}
                      </span>
                      {meta ? (
                        <span
                          className={cn(
                            "truncate text-xs",
                            status === "current" ? "text-lichen" : "text-sidebar-foreground/50",
                          )}
                        >
                          {meta}
                        </span>
                      ) : null}
                    </span>
                  ) : null}
                  <span className="sr-only">
                    {status === "done" ? " ✓" : status === "current" ? ` — ${t.journey.stepOf(i + 1, JOURNEY.length)}` : ""}
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      </div>

      <div>
        {!collapsed ? (
          <p className="px-2.5 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
            {t.journey.library}
          </p>
        ) : null}
        <div className="flex flex-col gap-1">
          {LIBRARY.map((item) => {
            const Icon = item.icon;
            const label = t.nav.items[item.key];
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                title={collapsed ? label : undefined}
                aria-current={pathname === item.href ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                  collapsed && "justify-center px-0",
                  pathname === item.href
                    ? "bg-sidebar-accent font-medium text-sidebar-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" />
                {!collapsed ? <span className="min-w-0 truncate">{label}</span> : null}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

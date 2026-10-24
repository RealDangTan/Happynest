"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CornerDownLeft,
  FileText,
  Inbox,
  MessageSquarePlus,
  Search,
  Upload,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useChat } from "./chat-provider";
import { apiFetch } from "@/lib/api";
import { STAGES, UTILITY_SCREENS } from "@/lib/navigation";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { FeedbackListResponse, InsightsListResponse } from "@/lib/types";

type PaletteItem = {
  key: string;
  group: string;
  label: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
};

export function CommandPalette({
  open,
  onOpenChange,
  productId,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  productId: string | null;
}) {
  const router = useRouter();
  const { openChat } = useChat();
  const t = useT();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const [reports, setReports] = useState<InsightsListResponse | null>(null);
  const [feedbacks, setFeedbacks] = useState<FeedbackListResponse | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const go = (href: string) => {
    onOpenChange(false);
    router.push(href);
  };

  // Debounced lookups once the query is meaningful. Results persist between
  // keystrokes — short queries simply don't render report/feedback groups.
  useEffect(() => {
    if (!open || query.trim().length < 2) return;
    const timer = setTimeout(() => {
      const q = query.trim().toLowerCase();
      apiFetch<InsightsListResponse>(
        `/api/insights${productId ? `?product_id=${productId}` : ""}`,
      )
        .then((d) =>
          setReports({
            ...d,
            items: d.items.filter((i) => i.title.toLowerCase().includes(q)),
          }),
        )
        .catch(() => setReports(null));
      apiFetch<FeedbackListResponse>(
        `/api/feedbacks?limit=100${productId ? `&product_id=${productId}` : ""}`,
      )
        .then((d) =>
          setFeedbacks({
            ...d,
            items: d.items.filter((f) =>
              (f.feedback_text ?? "").toLowerCase().includes(q),
            ),
          }),
        )
        .catch(() => setFeedbacks(null));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, open, productId]);

  const items = useMemo<PaletteItem[]>(() => {
    const q = query.trim().toLowerCase();
    const list: PaletteItem[] = [];

    list.push({
      key: "cmd-import",
      group: t.palette.groupActions,
      label: t.palette.importCsv,
      icon: Upload,
      run: () => go("/importer"),
    });
    list.push({
      key: "cmd-chat",
      group: t.palette.groupActions,
      label: t.palette.startInvestigation,
      icon: MessageSquarePlus,
      run: () => {
        onOpenChange(false);
        openChat(null);
      },
    });

    for (const stage of STAGES) {
      for (const item of stage.items) {
        const label = t.nav.items[item.key];
        if (q && !label.toLowerCase().includes(q)) continue;
        list.push({
          key: `screen-${item.href}`,
          group: t.palette.groupScreens,
          label,
          hint: t.nav.groups[stage.group],
          icon: item.icon,
          run: () => go(item.href),
        });
      }
    }

    // Màn ngoại lai — tìm được từ palette như mọi màn hình khác.
    for (const item of UTILITY_SCREENS) {
      const { label, description } = t.nav.utility[item.key];
      if (
        q &&
        !label.toLowerCase().includes(q) &&
        !description.toLowerCase().includes(q)
      )
        continue;
      list.push({
        key: `util-${item.href}`,
        group: t.palette.groupApp,
        label,
        icon: item.icon,
        run: () => go(item.href),
      });
    }

    for (const r of query.trim().length >= 2 ? reports?.items.slice(0, 5) ?? [] : []) {
      list.push({
        key: `report-${r.id}`,
        group: t.palette.groupReports,
        label: r.title,
        hint: r.status,
        icon: FileText,
        run: () => go(`/reports?report=${r.id}`),
      });
    }

    for (const f of query.trim().length >= 2 ? feedbacks?.items.slice(0, 5) ?? [] : []) {
      list.push({
        key: `fb-${f.id}`,
        group: t.palette.groupFeedback,
        label: f.feedback_text?.slice(0, 90) ?? f.id,
        hint: f.import_id ? `import ${f.import_id.slice(0, 8)}` : undefined,
        icon: Inbox,
        run: () => go(f.import_id ? `/vault?import=${f.import_id}` : "/vault"),
      });
    }

    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, query, reports, feedbacks, productId]);

  // Derived so the selection stays valid while the item list shrinks/grows.
  const active = Math.min(index, Math.max(items.length - 1, 0));

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const grouped = useMemo(() => {
    const groups: { group: string; items: { item: PaletteItem; idx: number }[] }[] = [];
    items.forEach((item, idx) => {
      const last = groups.at(-1);
      if (last && last.group === item.group) last.items.push({ item, idx });
      else groups.push({ group: item.group, items: [{ item, idx }] });
    });
    return groups;
  }, [items]);

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) setQuery("");
      }}
    >
      <DialogContent className="top-20 translate-y-0 gap-0 overflow-hidden p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setIndex(Math.min(active + 1, items.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setIndex(Math.max(active - 1, 0));
              } else if (e.key === "Enter" && items[active]) {
                e.preventDefault();
                items[active].run();
              }
            }}
            placeholder={t.palette.placeholder}
            className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            aria-label="Search"
          />
          <kbd className="rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            Esc
          </kbd>
        </div>
        <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
          {items.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              {t.palette.empty(query)}
            </p>
          ) : (
            grouped.map(({ group, items: groupItems }) => (
              <div key={group} className="mb-1">
                <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group}
                </p>
                {groupItems.map(({ item, idx }) => (
                  <button
                    key={item.key}
                    data-idx={idx}
                    onClick={item.run}
                    onMouseEnter={() => setIndex(idx)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-sm outline-none",
                      idx === active
                        ? "bg-accent text-accent-foreground"
                        : "text-foreground/90",
                    )}
                  >
                    <item.icon className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    {item.hint ? (
                      <span className="shrink-0 whitespace-nowrap font-mono text-[10px] uppercase text-signal">
                        {item.hint}
                      </span>
                    ) : null}
                    {idx === active ? (
                      <CornerDownLeft className="size-3.5 shrink-0 text-muted-foreground" />
                    ) : null}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

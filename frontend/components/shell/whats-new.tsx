"use client";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const NOTES = [
  {
    date: "2026-09-15",
    title: "New workspace shell",
    body: "Top navbar with global search (Ctrl K) and a collapsible Home/Chat panel.",
  },
  {
    date: "2026-09-15",
    title: "Six-screen journey",
    body: "Importer → Feedback Vault → Data Graph → Reports → Priority Matrix → Stakeholders, with all three human gates.",
  },
  {
    date: "2026-09-15",
    title: "Ask about your data",
    body: "Chat investigations now run the UNDERSTAND graph and deep-link drafts into Reports for review.",
  },
];

export function WhatsNew({
  tone = "navbar",
  compact = false,
}: {
  tone?: "panel" | "navbar";
  compact?: boolean;
}) {
  const label = useT().panel.whatsNew;
  const showLabel = tone === "panel" && !compact;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size={showLabel ? "default" : "icon"}
          className={cn(
            tone === "panel"
              ? "h-9 text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-sidebar-ring"
              : "size-8 text-muted-foreground hover:bg-accent hover:text-foreground",
            tone === "panel" && (showLabel ? "justify-start px-3" : "w-9"),
          )}
          aria-label={label}
          title={showLabel ? undefined : label}
        >
          <Sparkles data-icon="inline-start" />
          {showLabel && label}
        </Button>
      </PopoverTrigger>
      <PopoverContent side={tone === "panel" && compact ? "right" : "top"} align="end" className="w-80 max-w-[calc(100vw-1rem)]">
        <p className="text-sm font-semibold">{label}</p>
        <ul className="mt-3 space-y-3">
          {NOTES.map((n) => (
            <li key={n.title} className="space-y-0.5">
              <p className="font-mono text-xs text-signal">{n.date}</p>
              <p className="text-sm font-medium">{n.title}</p>
              <p className="text-xs text-muted-foreground">{n.body}</p>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

"use client";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

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

export function WhatsNew({ tone = "navbar" }: { tone?: "panel" | "navbar" }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={
            tone === "panel"
              ? "size-8 text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              : "size-8 text-muted-foreground hover:bg-accent hover:text-foreground"
          }
          aria-label="What's new"
          title="What's new"
        >
          <Sparkles className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent side="top" align="end" className="w-80">
        <p className="text-sm font-semibold">What&apos;s new</p>
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

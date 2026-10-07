"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LifeBuoy,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { STAGES } from "@/lib/navigation";
import { ScrollArea } from "@/components/ui/scroll-area";
import { usePanel } from "./panel-provider";
import { useChat } from "./chat-provider";
import { ChatThread } from "./chat-thread";
import { SettingsDialog } from "./settings-dialog";
import { WhatsNew } from "./whats-new";

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        collapsed && "justify-center px-0",
        active
          ? "bg-sidebar-accent font-medium text-sidebar-foreground"
          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      {!collapsed ? <span className="truncate">{label}</span> : null}
    </Link>
  );
}

function SegmentButton({
  active,
  collapsed,
  label,
  icon: Icon,
  onClick,
}: {
  active: boolean;
  collapsed: boolean;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={cn(
        "flex items-center justify-center gap-1.5 rounded-md py-1 text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        collapsed && "px-0",
        !collapsed && "px-3",
        active
          ? "bg-sidebar-primary font-medium text-sidebar-primary-foreground"
          : "text-sidebar-foreground/70 hover:text-sidebar-foreground",
      )}
    >
      <Icon className="size-4" />
      {!collapsed ? label : null}
    </button>
  );
}

export function LeftPanel() {
  const { collapsed, toggle, setCollapsed, mobileOpen, setMobileOpen } = usePanel();
  const { chatOpen, openChat, closeChat } = useChat();
  const pathname = usePathname();
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Fully separate tabs: Chat replaces the dock content, Home brings it back.
  const tab: "home" | "chat" = chatOpen ? "chat" : "home";

  return (
    <>
      {/* mobile backdrop */}
      {mobileOpen ? (
        <div
          className="fixed inset-0 z-40 bg-foreground/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-sidebar text-sidebar-foreground transition-[width,transform] duration-200",
          tab === "chat" ? "w-80" : collapsed ? "w-14" : "w-64",
          // mobile: slide in/out
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* header */}
        <div
          className={cn(
            "flex h-14 shrink-0 items-center gap-2 px-4",
            collapsed && tab === "home" && "justify-center px-0",
          )}
        >
          <Link
            href="/importer"
            className="flex min-w-0 items-center gap-2 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
            onClick={() => {
              closeChat();
              setMobileOpen(false);
            }}
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-lichen/20 font-heading text-sm font-semibold text-lichen">
              H
            </span>
            {!(collapsed && tab === "home") ? (
              <span className="truncate font-heading text-base">Happynest</span>
            ) : null}
          </Link>
          {tab === "home" && !collapsed ? (
            <button
              onClick={toggle}
              className="ml-auto rounded-md p-1.5 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              aria-label="Collapse panel"
              title="Collapse panel"
            >
              <PanelLeftClose className="size-4" />
            </button>
          ) : null}
        </div>
        {tab === "home" && collapsed ? (
          <button
            onClick={toggle}
            className="mx-auto mb-2 rounded-md p-1.5 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
            aria-label="Expand panel"
            title="Expand panel"
          >
            <PanelLeftOpen className="size-4" />
          </button>
        ) : null}

        {/* segmented control */}
        <div
          className={cn(
            "shrink-0 px-4 pb-4",
            collapsed && tab === "home" && "flex flex-col items-center gap-1 px-0",
          )}
        >
          <div
            className={cn(
              "grid gap-1 rounded-lg bg-sidebar-accent/60 p-1",
              collapsed && tab === "home" ? "grid-cols-1" : "grid-cols-2",
            )}
            role="tablist"
            aria-label="Panel sections"
          >
            <SegmentButton
              active={tab === "home"}
              collapsed={collapsed && tab === "home"}
              label="Home"
              icon={() => (
                <svg viewBox="0 0 24 24" fill="none" className="size-4">
                  <path
                    d="M3 10.5 12 3l9 7.5M5 9.5V21h5v-6h4v6h5V9.5"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
              onClick={() => closeChat()}
            />
            <SegmentButton
              active={tab === "chat"}
              collapsed={false}
              label="Chat"
              icon={({ className }) => (
                <svg viewBox="0 0 24 24" fill="none" className={className ?? "size-4"}>
                  <path
                    d="M21 12a8 8 0 0 1-8 8H4l2.2-3.1A8 8 0 1 1 21 12Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
              // Re-opening an active chat keeps its thread — only a closed tab starts fresh.
              onClick={() => {
                if (!chatOpen) openChat();
                setCollapsed(false);
                setMobileOpen(false);
              }}
            />
          </div>
        </div>

        {/* Home tab: the six-screen journey + frozen utilities footer */}
        <div className={cn("min-h-0 flex-1 flex-col", tab === "home" ? "flex" : "hidden")}>
          <ScrollArea className="min-h-0 flex-1">
            <nav
              className={cn(
                "px-4 pb-4",
                collapsed && "flex flex-col items-center",
              )}
              aria-label="Panel"
            >
              <div className="w-full space-y-5">
                {STAGES.map((stage) => (
                  <div key={stage.group}>
                    {!collapsed ? (
                      <p className="px-2.5 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                        {stage.group}
                      </p>
                    ) : null}
                    <div className="space-y-1">
                      {stage.items.map((item) => (
                        <NavItem
                          key={item.href}
                          href={item.href}
                          label={item.label}
                          icon={item.icon}
                          active={pathname === item.href}
                          collapsed={collapsed}
                          onNavigate={() => setMobileOpen(false)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </nav>
          </ScrollArea>

          <div
            className={cn(
              "shrink-0 border-t border-sidebar-border/60 px-4 py-3",
              collapsed && "flex flex-col items-center gap-1 px-0",
            )}
          >
            <div className={cn("flex items-center gap-1", collapsed ? "flex-col" : "justify-end")}>
              <button
                onClick={() => setSettingsOpen(true)}
                title="Settings"
                aria-label="Settings"
                className="rounded-md p-1.5 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              >
                <Settings className="size-4" />
              </button>
              <Link
                href="/qna"
                title="Contact us"
                aria-label="Contact us"
                className="rounded-md p-1.5 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              >
                <LifeBuoy className="size-4" />
              </Link>
              <WhatsNew tone="panel" />
            </div>
            {!collapsed ? (
              <p className="pb-1 pr-1 font-mono text-[10px] text-sidebar-foreground/40">
                Happynest VoC OS
              </p>
            ) : null}
          </div>
        </div>

        {/* Chat tab: the dock becomes the chat — no utilities footer */}
        <div className={cn("min-h-0 flex-1", tab === "chat" ? "flex" : "hidden")}>
          <ChatThread />
        </div>
      </aside>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}

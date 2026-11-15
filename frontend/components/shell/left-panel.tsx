"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { House, LifeBuoy, MessageCircle, PanelLeftClose, PanelLeftOpen, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { STAGES, STAGE_TONE, TONE_CLASSES, type StageTone } from "@/lib/navigation";
import { useT } from "@/lib/i18n";
import { useJourney } from "@/hooks/use-journey";
import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { usePanel } from "./panel-provider";
import { useChat } from "./chat-provider";
import { ChatThread } from "./chat-thread";
import { WhatsNew } from "./whats-new";

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
  tone,
  badge,
  badgeTitle,
  isNext,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  collapsed: boolean;
  tone: StageTone;
  /** Số việc đang chờ ở màn này (0 = ẩn). */
  badge: number;
  badgeTitle?: string;
  /** Màn chứa bước tiếp theo của luồng — chấm nhỏ, không ép thứ tự. */
  isNext: boolean;
  onNavigate?: () => void;
}) {
  const toneClass = TONE_CLASSES[tone];
  return (
    <Link
      href={href}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      aria-label={collapsed ? [label, badgeTitle].filter(Boolean).join(" — ") : undefined}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        "before:absolute before:inset-y-1.5 before:left-0 before:w-[3px] before:rounded-full before:opacity-0 before:transition-opacity",
        toneClass.bar,
        collapsed && "mx-auto size-9 justify-center rounded-lg p-0",
        active
          ? "bg-sidebar-accent font-medium text-sidebar-foreground before:opacity-100"
          : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      {!collapsed ? <span className="min-w-0 flex-1 truncate">{label}</span> : null}
      {badge > 0 ? (
        <span
          title={badgeTitle}
          className={cn(
            "rounded-full px-1.5 py-px font-mono text-[10px] font-semibold leading-4",
            toneClass.chip,
            collapsed && "absolute -top-0.5 -right-0.5 px-1 leading-3.5",
          )}
        >
          {badge > 99 ? "99+" : badge}
          {badgeTitle ? <span className="sr-only"> — {badgeTitle}</span> : null}
        </span>
      ) : isNext ? (
        <span
          aria-hidden
          className={cn(
            "size-1.5 shrink-0 rounded-full",
            toneClass.dot,
            collapsed && "absolute top-1 right-1",
          )}
        />
      ) : null}
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
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={cn(
        "flex min-w-0 items-center justify-center gap-1.5 rounded-md py-1 text-sm whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        collapsed ? "size-8 p-0" : "px-2",
        active
          ? "bg-sidebar-primary font-medium text-sidebar-primary-foreground"
          : "text-sidebar-foreground/70 hover:text-sidebar-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      {!collapsed ? <span className="min-w-0 truncate">{label}</span> : null}
    </button>
  );
}

export function LeftPanel() {
  const { collapsed, toggle, mobileOpen, setMobileOpen } = usePanel();
  const { chatOpen, openChat, closeChat } = useChat();
  const pathname = usePathname();
  const t = useT();
  // Số việc chờ theo màn — chỉ là gợi ý, điều hướng vẫn tự do theo ba chặng.
  const { journey } = useJourney();
  const nextPath = journey ? journey.next.href.split("?")[0] : null;
  const badges: Record<string, { count: number; title?: string }> = journey
    ? {
        "/vault": {
          count: journey.steps.classify.count ?? 0,
          title: t.journey.meta.pending(journey.steps.classify.count ?? 0),
        },
        "/data-graph": {
          count: journey.steps.investigate.count ?? 0,
          title: t.journey.meta.review(journey.steps.investigate.count ?? 0),
        },
        "/matrix": {
          count: journey.steps.act.count ?? 0,
          title: t.journey.meta.open(journey.steps.act.count ?? 0),
        },
      }
    : {};
  // Fully separate tabs: Chat replaces the dock content, Home brings it back.
  const tab: "home" | "chat" = chatOpen ? "chat" : "home";
  const compact = tab === "home" && collapsed && !mobileOpen;
  const utilities = [
    { href: "/help", label: t.panel.helpContact, icon: LifeBuoy },
    { href: "/settings", label: t.profile.settings, icon: Settings },
  ];

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
          "fixed inset-y-0 left-0 z-50 flex max-w-full flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width,transform] duration-200 motion-reduce:transition-none",
          tab === "chat" ? "w-80" : compact ? "w-14" : "w-64",
          // mobile: slide in/out
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* header */}
        <div
          className={cn(
            "flex h-14 shrink-0 items-center gap-2 px-4",
            compact && "justify-center px-0",
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
            <BrandMark />
            {!compact ? (
              <span className="truncate font-heading text-base">Happynest</span>
            ) : null}
          </Link>
          {tab === "home" && !compact ? (
            <button
              onClick={toggle}
              className="ml-auto hidden rounded-md p-1.5 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring md:block"
              aria-label={t.panel.collapse}
              title={t.panel.collapse}
            >
              <PanelLeftClose className="size-4" />
            </button>
          ) : null}
        </div>
        {compact ? (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="mx-auto mb-2 size-9 shrink-0 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-sidebar-ring"
            aria-label={t.panel.expand}
            title={t.panel.expand}
          >
            <PanelLeftOpen className="size-4" />
          </Button>
        ) : null}

        {/* segmented control */}
        <div
          className={cn(
            "shrink-0 px-4 pb-4",
            compact && "flex justify-center px-0 pb-3",
          )}
        >
          <div
            className={cn(
              "grid gap-1 rounded-lg bg-sidebar-accent/60 p-1",
              compact ? "grid-cols-1" : "grid-cols-2",
            )}
            role="group"
            aria-label={t.panel.sections}
          >
            <SegmentButton
              active={tab === "home"}
              collapsed={compact}
              label={t.panel.home}
              icon={House}
              onClick={() => closeChat()}
            />
            <SegmentButton
              active={tab === "chat"}
              collapsed={compact}
              label={t.panel.chat}
              icon={MessageCircle}
              onClick={() => {
                if (!chatOpen) openChat();
              }}
            />
          </div>
        </div>

        {/* Home tab: the six-screen journey + frozen utilities footer */}
        <div className={cn("min-h-0 flex-1 flex-col", tab === "home" ? "flex" : "hidden")}>
          <ScrollArea className="min-h-0 flex-1">
            <nav
              className={cn(
                "pb-4",
                compact ? "px-1" : "px-4",
              )}
              aria-label="Panel"
            >
              <div className={cn("flex w-full flex-col", compact ? "gap-2" : "gap-5")}>
                {STAGES.map((stage, index) => (
                  <div key={stage.group} role="group" aria-label={t.nav.groups[stage.group]}>
                    {compact && index > 0 ? (
                      <Separator className="mx-auto mb-2 bg-sidebar-foreground/15 data-horizontal:w-6" />
                    ) : null}
                    {!compact ? (
                      <p className="flex items-center gap-2 px-2.5 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/55">
                        <span
                          aria-hidden
                          className={cn(
                            "size-2 rounded-full",
                            TONE_CLASSES[STAGE_TONE[stage.group]].dot,
                          )}
                        />
                        {t.nav.groups[stage.group]}
                      </p>
                    ) : null}
                    <div className="flex flex-col gap-1">
                      {stage.items.map((item) => (
                        <NavItem
                          key={item.href}
                          href={item.href}
                          label={t.nav.items[item.key]}
                          icon={item.icon}
                          active={pathname === item.href}
                          collapsed={compact}
                          tone={STAGE_TONE[stage.group]}
                          badge={badges[item.href]?.count ?? 0}
                          badgeTitle={badges[item.href]?.title}
                          isNext={nextPath === item.href && pathname !== item.href}
                          onNavigate={() => setMobileOpen(false)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </nav>
          </ScrollArea>

          <nav
            aria-label={t.panel.utilities}
            className={cn(
              "flex shrink-0 flex-col gap-1 border-t border-sidebar-foreground/10 py-2.5",
              compact ? "items-center px-1" : "px-3",
            )}
          >
            <WhatsNew tone="panel" compact={compact} />
            {utilities.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Button
                  key={href}
                  variant="ghost"
                  size={compact ? "icon" : "default"}
                  className={cn(
                    "h-9 text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-sidebar-ring",
                    compact ? "w-9" : "justify-start px-3",
                    active && "bg-sidebar-accent text-sidebar-foreground",
                  )}
                  asChild
                >
                  <Link
                    href={href}
                    title={compact ? label : undefined}
                    aria-label={label}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setMobileOpen(false)}
                  >
                    <Icon data-icon="inline-start" />
                    {!compact && label}
                  </Link>
                </Button>
              );
            })}
          </nav>
        </div>

        {/* Chat tab: the dock becomes the chat — no utilities footer */}
        <div className={cn("min-h-0 flex-1", tab === "chat" ? "flex" : "hidden")}>
          <ChatThread />
        </div>
      </aside>
    </>
  );
}

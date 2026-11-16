"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LifeBuoy, Mail, SlidersHorizontal, SunMoon, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";

const SECTIONS: {
  label: string;
  items: { href: string; label: string; icon: React.ComponentType<{ className?: string }> }[];
}[] = [
  {
    label: "Tài khoản",
    items: [
      { href: "/profile", label: "Hồ sơ", icon: UserRound },
      { href: "/settings", label: "Tuỳ chọn", icon: SunMoon },
    ],
  },
  {
    label: "Workspace",
    items: [{ href: "/settings/workspace", label: "Chung", icon: SlidersHorizontal }],
  },
  {
    label: "Hỗ trợ",
    items: [
      { href: "/help", label: "Trợ giúp", icon: LifeBuoy },
      { href: "/contact", label: "Liên hệ", icon: Mail },
    ],
  },
];

/**
 * Khung chung cho Hồ sơ / Tuỳ chọn / Workspace (mẫu Twenty Settings): mục lục
 * cố định bên trái nhóm theo Tài khoản · Workspace · Hỗ trợ, nội dung bên phải.
 * Ở màn hẹp mục lục thành một hàng cuộn ngang.
 */
export function SettingsShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[12rem_minmax(0,1fr)]">
      <nav aria-label="Mục cài đặt" className="lg:sticky lg:top-20">
        <ul className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:flex-col lg:gap-4 lg:overflow-visible">
          {SECTIONS.map((section) => (
            <li key={section.label} className="flex shrink-0 gap-1 lg:flex-col">
              <p className="hidden px-2 pb-1 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase lg:block">
                {section.label}
              </p>
              {section.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      active ? "bg-accent font-medium text-accent-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                    )}
                  >
                    <item.icon className="size-4 shrink-0" />
                    {item.label}
                  </Link>
                );
              })}
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex min-w-0 max-w-3xl flex-col gap-6">{children}</div>
    </div>
  );
}

/** Một hàng trong vùng nguy hiểm: mô tả bên trái, nút bên phải. */
export function DangerRow({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-t border-destructive/20 py-4 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex min-w-0 max-w-prose flex-col gap-0.5">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="shrink-0">{action}</div>
    </div>
  );
}

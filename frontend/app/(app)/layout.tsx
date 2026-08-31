"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMe } from "@/hooks/use-me";
import { apiFetch } from "@/lib/api";
import { ActivityProvider } from "@/components/activity/activity-provider";
import { ActivityNavButton } from "@/components/activity/activity-nav-button";
import {
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Activity,
  Layers,
  Lightbulb,
  FileBarChart,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/feedbacks", label: "Phản hồi", icon: MessageSquareText },
  { href: "/analysis", label: "Analysis", icon: Activity },
  { href: "/clusters", label: "Clusters", icon: Layers },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/reports", label: "Báo cáo", icon: FileBarChart },
];

const PHASE_LABEL: Record<string, string> = {
  "/clusters": "Pha P3",
  "/insights": "Pha P4",
  "/reports": "Pha P4",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const queryClient = useQueryClient();
  const initials = (me.data?.email ?? "?").slice(0, 2).toUpperCase();

  const logout = useMutation({
    mutationFn: () => apiFetch("/api/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });

  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
    <ActivityProvider>
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="px-4 py-3 font-heading text-lg">
          Happynest
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Menu</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {NAV.map(({ href, label, icon: Icon }) => (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton asChild>
                      <Link href={href}>
                        <Icon data-icon="inline-start" />
                        {label}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter className="p-3">
          <DropdownMenu>
            <DropdownMenuTrigger className="flex w-full items-center gap-2 rounded-md text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Avatar className="size-8">
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{me.data?.email ?? "…"}</p>
              </div>
              {me.data ? (
                <Badge variant="secondary">{me.data.role}</Badge>
              ) : null}
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="start" className="w-56">
              <DropdownMenuLabel className="truncate">
                {me.data?.email ?? "…"}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                disabled={logout.isPending}
                onSelect={() => logout.mutate()}
              >
                <LogOut data-icon="inline-start" />
                Đăng xuất
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <header className="flex h-14 items-center gap-2 px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-6" />
          <span className="text-sm text-muted-foreground">
            AI Feedback Agent — bản demo luận văn
          </span>
          <ActivityNavButton />
        </header>
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
    </ActivityProvider>
    </Suspense>
  );
}

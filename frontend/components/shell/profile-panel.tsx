"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import {
  Boxes,
  Languages,
  LogOut,
  Moon,
  Settings,
  SlidersHorizontal,
  Sun,
  UserRound,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useMe } from "@/hooks/use-me";
import { useAppLanguage } from "@/hooks/use-language";
import { useProduct } from "@/hooks/use-product";
import { apiFetch } from "@/lib/api";

export function ProfilePanel() {
  const me = useMe();
  const { product } = useProduct();
  const { resolvedTheme, setTheme } = useTheme();
  const { lang, applyLang } = useAppLanguage();
  const router = useRouter();
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
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="flex h-8 items-center gap-1.5 rounded-full border border-border/80 bg-card pl-1 pr-2.5 shadow-sm outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Profile menu"
        >
          <Avatar className="size-6">
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 gap-1 p-2">
        <div className="flex items-center gap-3 px-2 py-1.5">
          <Avatar className="size-9">
            <AvatarFallback className="text-sm">{initials}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {me.data?.email ?? "…"}
            </p>
          </div>
        </div>
        <Separator />
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm">
          <Boxes className="size-4 shrink-0 text-muted-foreground" />
          <span className="text-muted-foreground">Workspace</span>
          <span className="ml-auto min-w-0 truncate font-medium">
            {product?.name ?? "—"}
          </span>
        </div>
        <Button variant="ghost" size="sm" asChild className="justify-start">
          <Link href="/settings/workspace">
            <SlidersHorizontal data-icon="inline-start" />
            Workspace settings
          </Link>
        </Button>
        <Button variant="ghost" size="sm" asChild className="justify-start">
          <Link href="/profile">
            <UserRound data-icon="inline-start" />
            Profile
          </Link>
        </Button>
        <Button variant="ghost" size="sm" asChild className="justify-start">
          <Link href="/settings">
            <Settings data-icon="inline-start" />
            Settings
          </Link>
        </Button>
        <Separator />
        <div className="flex items-center gap-2 px-2 py-1.5 text-sm">
          <Languages className="size-4 shrink-0 text-muted-foreground" />
          <span className="text-muted-foreground">Language</span>
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            spacing={0}
            className="ml-auto"
            value={lang}
            onValueChange={(v) => {
              if (v === "vi" || v === "en") applyLang(v);
            }}
          >
            <ToggleGroupItem value="vi" className="h-7 px-2.5 text-xs">
              VI
            </ToggleGroupItem>
            <ToggleGroupItem value="en" className="h-7 px-2.5 text-xs">
              EN
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <div className="flex items-center gap-2 px-2 py-1.5 text-sm">
          {resolvedTheme === "dark" ? (
            <Moon className="size-4 shrink-0 text-muted-foreground" />
          ) : (
            <Sun className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="text-muted-foreground">Theme</span>
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            spacing={0}
            className="ml-auto"
            value={resolvedTheme ?? "light"}
            onValueChange={(v) => {
              if (v === "light" || v === "dark") setTheme(v);
            }}
          >
            <ToggleGroupItem
              value="light"
              aria-label="Light theme"
              className="h-7 px-2"
            >
              <Sun className="size-3.5" />
            </ToggleGroupItem>
            <ToggleGroupItem
              value="dark"
              aria-label="Dark theme"
              className="h-7 px-2"
            >
              <Moon className="size-3.5" />
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <Separator />
        <Button
          variant="ghost"
          size="sm"
          disabled={logout.isPending}
          className="justify-start text-destructive hover:text-destructive"
          onClick={() => logout.mutate()}
        >
          <LogOut data-icon="inline-start" />
          Sign out
        </Button>
      </PopoverContent>
    </Popover>
  );
}

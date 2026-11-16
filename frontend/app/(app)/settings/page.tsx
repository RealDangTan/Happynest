"use client";
import { useTheme } from "next-themes";
import {
  Languages,
  Moon,
  ShieldCheck,
  Sun,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { LangToggle } from "@/components/lang-toggle";
import { PageHeader } from "@/components/page-header";
import { useT } from "@/lib/i18n";
import { SettingsShell } from "@/components/settings/settings-shell";

/** Hàng tuỳ chọn: icon + nhãn bên trái, control đẩy sang phải — cùng nhịp
 * với profile popover để hai chỗ nhìn là biết cùng một thiết lập. */
function PrefRow({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 text-sm">
      <div className="flex min-w-0 items-center gap-3">
        <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">{label}</span>
      </div>
      <div className="ml-auto shrink-0">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useT();
  return (
    <SettingsShell>
      <PageHeader title={t.settings.title} description={t.settings.description} />

      <Card>
        <CardHeader>
          <CardTitle>{t.settings.appearanceTitle}</CardTitle>
          <CardDescription>{t.settings.appearanceDescription}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <PrefRow icon={resolvedTheme === "dark" ? Moon : Sun} label={t.settings.theme}>
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              spacing={0}
              value={resolvedTheme ?? "light"}
              onValueChange={(v) => {
                if (v === "light" || v === "dark") setTheme(v);
              }}
            >
              <ToggleGroupItem
                value="light"
                aria-label={t.settings.light}
                className="h-7 px-2.5 text-xs"
              >
                {t.settings.light}
              </ToggleGroupItem>
              <ToggleGroupItem
                value="dark"
                aria-label={t.settings.dark}
                className="h-7 px-2.5 text-xs"
              >
                {t.settings.dark}
              </ToggleGroupItem>
            </ToggleGroup>
          </PrefRow>
          <PrefRow icon={Languages} label={t.settings.language}>
            <LangToggle />
          </PrefRow>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.settings.privacyTitle}</CardTitle>
          <CardDescription>{t.settings.privacyDescription}</CardDescription>
        </CardHeader>
        <CardContent className="flex-row items-start gap-3 text-sm">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-lichen" />
          <p className="min-w-0 max-w-prose text-muted-foreground">
            {t.settings.privacyBodyBefore}
            <code className="font-mono text-xs">&lt;TYPE&gt;</code>
            {t.settings.privacyBodyAfter}{" "}
            <Badge variant="secondary" className="ml-1">
              Presidio + Stanza VI
            </Badge>
          </p>
        </CardContent>
      </Card>
    </SettingsShell>
  );
}

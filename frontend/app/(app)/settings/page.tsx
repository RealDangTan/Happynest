"use client";
import Link from "next/link";
import { useTheme } from "next-themes";
import {
  ChevronRight,
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
import { PageHeader } from "@/components/page-header";
import { useAppLanguage } from "@/hooks/use-language";
import { UTILITY_SCREENS } from "@/lib/navigation";

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
    <div className="flex items-center gap-3 text-sm">
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      <div className="ml-auto">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const { resolvedTheme, setTheme } = useTheme();
  const { lang, applyLang } = useAppLanguage();
  const shortcuts = UTILITY_SCREENS.filter((s) => s.href !== "/settings");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="Tuỳ chỉnh ứng dụng theo tài khoản — lưu trên trình duyệt này, áp dụng cho mọi workspace."
      />

      {/* Lối vào nhanh các màn ngoại lai còn lại */}
      <div className="grid gap-3 sm:grid-cols-2">
        {shortcuts.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="group outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
          >
            <Card size="sm" className="transition-colors group-hover:bg-accent/50">
              <CardContent className="flex items-center gap-3">
                <s.icon className="size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{s.label}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {s.description}
                  </p>
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Giao diện</CardTitle>
          <CardDescription>Chủ đề màu áp dụng ngay lập tức.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <PrefRow icon={resolvedTheme === "dark" ? Moon : Sun} label="Chủ đề">
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
              <ToggleGroupItem value="light" aria-label="Sáng" className="h-7 px-2.5 text-xs">
                Sáng
              </ToggleGroupItem>
              <ToggleGroupItem value="dark" aria-label="Tối" className="h-7 px-2.5 text-xs">
                Tối
              </ToggleGroupItem>
            </ToggleGroup>
          </PrefRow>
          <PrefRow icon={Languages} label="Ngôn ngữ">
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              spacing={0}
              value={lang}
              onValueChange={applyLang}
            >
              <ToggleGroupItem value="vi" className="h-7 px-2.5 text-xs">
                VI
              </ToggleGroupItem>
              <ToggleGroupItem value="en" className="h-7 px-2.5 text-xs">
                EN
              </ToggleGroupItem>
            </ToggleGroup>
          </PrefRow>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dữ liệu & riêng tư</CardTitle>
          <CardDescription>
            Ranh giới PII là bất biến của pipeline — không có công tắc để tắt.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-start gap-3 text-sm">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-lichen" />
          <p className="max-w-prose text-muted-foreground">
            Mọi feedback đi qua bộ PII sanitizer (email, số điện thoại, CCCD…
            thay bằng placeholder <code className="font-mono text-xs">&lt;TYPE&gt;</code>)
            trước khi vào prompt, log hay trace của agent. Nội dung thô chỉ nằm
            trong database, không bao giờ rời ranh giới sanitize.{" "}
            <Badge variant="secondary" className="ml-1">
              Presidio + Stanza VI
            </Badge>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

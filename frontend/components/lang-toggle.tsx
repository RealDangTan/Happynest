"use client";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { setAppLang, useAppLang } from "@/lib/i18n";

/** Công tắc VI/EN dùng chung một nguồn (lib/i18n) — popover profile, trang
 * /settings và màn auth đều render cùng một control để nhận ra là một thiết lập. */
export function LangToggle({ className }: { className?: string }) {
  const lang = useAppLang();
  return (
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      spacing={0}
      className={className}
      value={lang}
      onValueChange={(v) => {
        if (v === "vi" || v === "en") setAppLang(v);
      }}
    >
      <ToggleGroupItem value="vi" className="h-7 px-2.5 text-xs">
        VI
      </ToggleGroupItem>
      <ToggleGroupItem value="en" className="h-7 px-2.5 text-xs">
        EN
      </ToggleGroupItem>
    </ToggleGroup>
  );
}

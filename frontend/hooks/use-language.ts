"use client";
import { useState } from "react";

const LANG_STORAGE_KEY = "happynest.lang";
export type AppLang = "vi" | "en";

function readSavedLang(): AppLang {
  if (
    typeof window !== "undefined" &&
    localStorage.getItem(LANG_STORAGE_KEY) === "en"
  ) {
    return "en";
  }
  return "vi";
}

/**
 * Ngôn ngữ hiển thị — một khoá localStorage duy nhất ("happynest.lang") dùng
 * chung bởi profile popover và trang /settings, đổi ở đâu cũng áp dụng ở chỗ kia.
 */
export function useAppLanguage() {
  const [lang, setLang] = useState<AppLang>(readSavedLang);

  const applyLang = (next: string) => {
    if (next !== "vi" && next !== "en") return;
    setLang(next);
    localStorage.setItem(LANG_STORAGE_KEY, next);
    document.documentElement.lang = next;
  };

  return { lang, applyLang };
}

"use client";
import { useEffect } from "react";

/**
 * Đặt document.title cho các page client component (không export được
 * `metadata` của Next). Format khớp template metadata server:
 * "<title> — Happynest".
 */
export function usePageTitle(title?: string) {
  useEffect(() => {
    if (!title) return;
    document.title = `${title} — Happynest`;
  }, [title]);
}

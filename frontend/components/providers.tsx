"use client";
import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { useAppLang } from "@/lib/i18n";
import { TooltipProvider } from "@/components/ui/tooltip";

/** Giữ thuộc tính `lang` của <html> khớp ngôn ngữ hiển thị (mặc định vi,
 * đúng lại ngay sau hydrate nếu người dùng đã lưu "en"). */
function HtmlLangSync() {
  const lang = useAppLang();
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <HtmlLangSync />
      <TooltipProvider>{children}</TooltipProvider>
    </QueryClientProvider>
  );
}

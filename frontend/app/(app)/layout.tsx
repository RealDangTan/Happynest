"use client";
import { Suspense } from "react";
import { cn } from "@/lib/utils";
import { PanelProvider, usePanel } from "@/components/shell/panel-provider";
import { ChatProvider, useChat } from "@/components/shell/chat-provider";
import { ProductProvider } from "@/hooks/use-product";
import { ActivityProvider } from "@/components/activity/activity-provider";
import { LeftPanel } from "@/components/shell/left-panel";
import { TopNavbar } from "@/components/shell/top-navbar";

function Shell({ children }: { children: React.ReactNode }) {
  const { collapsed } = usePanel();
  const { chatOpen } = useChat();
  return (
    <div className="min-h-screen bg-background">
      <LeftPanel />
      <TopNavbar />
      <div
        className={cn(
          "min-w-0 overflow-x-clip transition-[padding] duration-200",
          chatOpen ? "md:pl-80" : collapsed ? "md:pl-14" : "md:pl-64",
        )}
      >
        <main className="min-h-screen px-4 pb-16 pt-20 md:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <PanelProvider>
        <ProductProvider>
          <ActivityProvider>
            <ChatProvider>
              <Shell>{children}</Shell>
            </ChatProvider>
          </ActivityProvider>
        </ProductProvider>
      </PanelProvider>
    </Suspense>
  );
}

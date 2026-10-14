"use client";
import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ArrowRight, FileSpreadsheet, PlayCircle, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useProduct } from "@/hooks/use-product";
import { useMe } from "@/hooks/use-me";

const dismissKey = (userId: string) =>
  `happynest.welcome-tour.dismissed.${userId}`;

const STEPS = [
  {
    stage: "LISTEN",
    icon: Plus,
    title: "Create your product",
    description:
      "One workspace per AI product — its feature, its users, its feedback.",
  },
  {
    stage: "LISTEN",
    icon: FileSpreadsheet,
    title: "Import your first CSV",
    description:
      "One column is required: the feedback text. You confirm the mapping before anything is stored.",
  },
  {
    stage: "UNDERSTAND",
    icon: PlayCircle,
    title: "Run your first analysis",
    description:
      "The agent clusters feedback and proposes insights — every insight waits for your review.",
  },
];

/**
 * Welcome tour cho account lần đầu vào app (isolation 0018: account mới
 * có workspace TRỐNG thật). Chỉ hiện khi user chưa có product nào và chưa
 * dismiss — key localStorage theo user id để 2 account trên cùng trình duyệt
 * không đè trạng thái của nhau.
 *
 * Giống FirstRunGuide: đọc localStorage trong render (SSR an toàn vì
 * products query vẫn pending lúc hydration → trả null). Không effect/state
 * phức tạp — open là trạng thái suy diễn.
 */
export function WelcomeTour() {
  const router = useRouter();
  const pathname = usePathname();
  const { products, loading } = useProduct();
  const me = useMe();
  // `closed` chỉ do sự kiện dismiss đặt (event handler) — không bao giờ
  // setState trong effect.
  const [closed, setClosed] = useState(false);

  const meData = me.data;
  const dismissedForUser =
    meData !== undefined &&
    typeof window !== "undefined" &&
    localStorage.getItem(dismissKey(meData.id)) === "1";

  // Đang ở trang /onboarding thì tour đè lên chính màn onboarding — nhường.
  if (
    loading ||
    !meData ||
    closed ||
    dismissedForUser ||
    pathname === "/onboarding" ||
    products.length > 0
  ) {
    return null;
  }

  const dismiss = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem(dismissKey(meData.id), "1");
    }
    setClosed(true);
  };

  return (
    <Dialog open onOpenChange={(v) => (v ? undefined : dismiss())}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            Welcome to Happynest
          </p>
          <DialogTitle className="font-heading text-xl">
            Three steps to your first insight
          </DialogTitle>
          <DialogDescription>
            Your workspace is empty — set it up once and the agent takes it
            from there.
          </DialogDescription>
        </DialogHeader>

        <ol className="divide-y rounded-xl border">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-3 px-4 py-3">
              <span
                aria-hidden
                className="flex size-8 shrink-0 items-center justify-center rounded-full bg-lichen/15 text-lichen"
              >
                <step.icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {String(i + 1).padStart(2, "0")} · {step.stage}
                </p>
                <h3 className="text-sm font-medium">{step.title}</h3>
                <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </li>
          ))}
        </ol>

        <div className="flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={dismiss}>
            Skip for now
          </Button>
          <Button
            onClick={() => {
              dismiss();
              router.push("/onboarding");
            }}
          >
            Start with your product
            <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

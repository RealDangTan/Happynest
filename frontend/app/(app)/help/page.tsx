"use client";
import Link from "next/link";
import { ChevronDown, ChevronRight, LifeBuoy } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { STAGES } from "@/lib/navigation";
import { useT } from "@/lib/i18n";

function FaqItem({ q, a }: { q: string; a: string }) {
  return (
    <details className="group rounded-lg border bg-card open:bg-secondary/40">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">{q}</span>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <p className="border-t px-4 py-3 text-sm leading-relaxed text-muted-foreground">
        {a}
      </p>
    </details>
  );
}

export default function HelpPage() {
  const t = useT();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t.help.title} description={t.help.description} />

      {/* Ba chặng của pipeline */}
      <div className="grid gap-4 md:grid-cols-3">
        {STAGES.map((stage, i) => (
          <Card key={stage.group} className="gap-3">
            <CardHeader>
              <p className="font-mono text-[11px] uppercase tracking-wider text-signal">
                {String(i + 1).padStart(2, "0")} · {t.nav.groups[stage.group]}
              </p>
              <CardDescription>
                {t.help.stageDescriptions[stage.group]}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              {stage.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <item.icon className="size-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">{t.nav.items[item.key]}</span>
                  <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/50" />
                </Link>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <CardHeader>
            <CardTitle>{t.help.faqTitle}</CardTitle>
            <CardDescription>{t.help.faqDescription}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {t.help.faqs.map((f) => (
              <FaqItem key={f.q} q={f.q} a={f.a} />
            ))}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6">
          <Card size="sm">
            <CardHeader>
              <CardTitle>{t.help.shortcutsTitle}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">
                  {t.help.shortcutSearch}
                </span>
                <kbd className="rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  Ctrl K
                </kbd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">
                  {t.help.shortcutClose}
                </span>
                <kbd className="rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  Esc
                </kbd>
              </div>
            </CardContent>
          </Card>

          <Card size="sm" className="bg-secondary/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LifeBuoy className="size-4 text-signal" />
                {t.help.stillWondering}
              </CardTitle>
              <CardDescription>
                {t.help.stillWonderingDescription}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/contact">
                  {t.help.openContactForm}
                  <ChevronRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

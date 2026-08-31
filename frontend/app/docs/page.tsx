import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/docs");

export const metadata: Metadata = { title: `Docs — Happynest`, description: page.description };

export default function DocsPage() {
  return <PublicPageShell page={page} />;
}


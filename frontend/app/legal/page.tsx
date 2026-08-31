import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/legal");

export const metadata: Metadata = { title: `Legal — Happynest`, description: page.description };

export default function LegalPage() {
  return <PublicPageShell page={page} />;
}

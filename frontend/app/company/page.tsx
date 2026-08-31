import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/company");

export const metadata: Metadata = { title: `Company — Happynest`, description: page.description };

export default function CompanyPage() {
  return <PublicPageShell page={page} />;
}


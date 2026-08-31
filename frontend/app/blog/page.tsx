import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/blog");

export const metadata: Metadata = { title: `Field notes — Happynest`, description: page.description };

export default function BlogPage() {
  return <PublicPageShell page={page} />;
}


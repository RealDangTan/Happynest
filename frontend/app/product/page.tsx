import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/product");

export const metadata: Metadata = { title: `Product — Happynest`, description: page.description };

export default function ProductPage() {
  return <PublicPageShell page={page} />;
}


import type { Metadata } from "next";
import { PublicPageShell } from "@/app/landing/public-page";
import { getMarketingPage } from "@/lib/marketing-content";

const page = getMarketingPage("/qna");

export const metadata: Metadata = { title: `Q&A — Happynest`, description: page.description };

export default function QnaPage() {
  return <PublicPageShell page={page} />;
}


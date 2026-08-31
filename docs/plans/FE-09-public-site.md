# Happynest Public Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `executing-plans` skill to implement this plan task-by-task INLINE (no subagents in this repo — limited LLM API credit). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the annotated full-viewport landing hero, a substantially longer evidence-led landing page, and complete public Product, Company, Blog, Docs, Q&A, and Legal pages.

**Architecture:** Keep the established landing visual system in `app/landing/`, extract shared public navigation/footer/page-shell primitives, and drive route copy from a typed marketing-content module. Middleware consumes one public-route contract so the site cannot drift from the routing guard.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, next/font, CSS/Tailwind 4, Vitest.

**Spec:** `docs/plans/FE-09-public-site-spec.md`

## Global Constraints

- No Docker and no new dependencies.
- Preserve the existing Happynest palette and pixel-nest identity.
- Use Lora only for the brand wordmark; keep Fraunces/Inter/Silkscreen roles intact.
- Public copy must describe actual repository capabilities and must not invent customers or production guarantees.
- All behavior changes follow RED → GREEN; verification requires tests, typecheck, build, and browser QA.

---

### Task 1: Public route and content contract

**Files:**
- Create: `frontend/lib/marketing-content.test.ts`
- Create: `frontend/lib/marketing-content.ts`
- Create: `frontend/lib/marketing-routes.ts`
- Modify: `frontend/middleware.ts`

**Interfaces:**
- Produces: `MARKETING_NAV`, `MARKETING_PAGES`, `PUBLIC_PATHS`, and `isPublicPath(pathname: string): boolean`.

- [x] **Step 1: Write the failing contract tests**

```ts
it("publishes every requested route without placeholder links", () => {
  expect(MARKETING_PAGES.map((page) => page.href)).toEqual([
    "/product", "/company", "/blog", "/docs", "/qna", "/legal",
  ])
  expect(JSON.stringify(MARKETING_PAGES)).not.toContain('"#"')
})
```

- [x] **Step 2: Run `pnpm test lib/marketing-content.test.ts` and confirm missing-module failure.**
- [x] **Step 3: Implement typed content and public-path helpers; wire middleware to `isPublicPath`.**
- [x] **Step 4: Re-run the focused test and confirm it passes.**

### Task 2: Shared public chrome and annotated hero

**Files:**
- Modify: `frontend/app/landing/fonts.ts`
- Modify: `frontend/app/landing/motion.tsx`
- Modify: `frontend/app/landing/landing.css`
- Modify: `frontend/app/landing/page.tsx`

**Interfaces:**
- Produces: `LandingNav`, `PublicFooter`, `HeroVideo`, `PublicPageShell`.

- [x] **Step 1: Add a source-contract test asserting the hero asset, mask asset, 0.5 playback rate, white logo, and 42px desktop headline token.**
- [x] **Step 2: Run the focused test and confirm it fails on the old placeholder hero.**
- [x] **Step 3: Add Lora, white-logo navigation, fixed route links, video playback-rate effect, full-height hero, and mask transition.**
- [x] **Step 4: Re-run focused tests and confirm green.**

### Task 3: Longer evidence-led landing

**Files:**
- Modify: `frontend/app/landing/page.tsx`
- Modify: `frontend/app/landing/landing.css`

**Interfaces:**
- Consumes: shared chrome and existing `Reveal`, `SignalField`, `ConfidenceRing`, `CountUp` primitives.
- Produces: source constellation, insight anatomy, three human gates, role outcomes, and FAQ preview sections.

- [x] **Step 1: Extend the source-contract test with required section IDs and factual copy markers.**
- [x] **Step 2: Run it and confirm the missing-section failure.**
- [x] **Step 3: Implement the sections with responsive editorial layouts and no placeholder links.**
- [x] **Step 4: Re-run focused tests and confirm green.**

### Task 4: Complete public route family

**Files:**
- Create: `frontend/app/product/page.tsx`
- Create: `frontend/app/company/page.tsx`
- Create: `frontend/app/blog/page.tsx`
- Create: `frontend/app/docs/page.tsx`
- Create: `frontend/app/qna/page.tsx`
- Create: `frontend/app/legal/page.tsx`
- Create: `frontend/app/landing/public-page.tsx`

**Interfaces:**
- Consumes: `MARKETING_PAGES`, `LandingNav`, `PublicFooter`.
- Produces: six statically rendered public pages with unique metadata, useful sections, and working cross-links.

- [x] **Step 1: Add tests requiring a title, description, eyebrow, and at least three substantial sections per page.**
- [x] **Step 2: Run focused tests and confirm failure until content is complete.**
- [x] **Step 3: Implement the shared shell and six route modules.**
- [x] **Step 4: Re-run focused tests and confirm green.**

### Task 5: Verification and visual QA

**Files:**
- Modify: `docs/plans/FE-00-index.md`
- Create: `docs/handoffs/2026-08-30-codex-public-site.md`

- [x] **Step 1: Run `pnpm test`.**
- [x] **Step 2: Run `pnpm typecheck`.**
- [x] **Step 3: Run `pnpm build` with the dev server stopped if memory pressure requires it.**
- [x] **Step 4: Browser-check `/landing` at desktop and mobile widths plus each public route; confirm hero video, mask, navigation, overflow, focus, and reduced-motion behavior.**
- [x] **Step 5: Mark FE-09 complete and leave an append-only handoff with exact evidence.**

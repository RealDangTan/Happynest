import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { MARKETING_NAV, MARKETING_PAGES } from "./marketing-content";
import { isPublicPath, PUBLIC_PATHS } from "./marketing-routes";

const readFrontendFile = (relativePath: string) =>
  readFileSync(fileURLToPath(new URL(`../${relativePath}`, import.meta.url)), "utf8");

describe("public marketing content", () => {
  it("publishes every requested route without placeholder links", () => {
    expect(MARKETING_PAGES.map((page) => page.href)).toEqual([
      "/product",
      "/company",
      "/blog",
      "/docs",
      "/qna",
      "/legal",
    ]);
    expect(JSON.stringify({ MARKETING_NAV, MARKETING_PAGES })).not.toContain('"#"');
  });

  it("gives every public page substantial unique content", () => {
    for (const page of MARKETING_PAGES) {
      expect(page.title.length).toBeGreaterThan(12);
      expect(page.description.length).toBeGreaterThan(60);
      expect(page.eyebrow.length).toBeGreaterThan(2);
      expect(page.sections.length).toBeGreaterThanOrEqual(3);
      expect(new Set(page.sections.map((section) => section.title)).size).toBe(
        page.sections.length,
      );
      for (const section of page.sections) {
        expect(section.body.length).toBeGreaterThan(80);
      }
    }
  });

  it("keeps every requested marketing route public", () => {
    expect(PUBLIC_PATHS).toContain("/landing");
    for (const page of MARKETING_PAGES) {
      expect(isPublicPath(page.href)).toBe(true);
      expect(isPublicPath(`${page.href}/example`)).toBe(true);
    }
    expect(isPublicPath("/dashboard")).toBe(false);
  });
});

describe("landing source contract", () => {
  it("uses the annotated hero media, mask, brand assets, and type scale", () => {
    const page = readFrontendFile("app/landing/page.tsx");
    const motion = readFrontendFile("app/landing/motion.tsx");
    const css = readFrontendFile("app/landing/landing.css");

    expect(page).toContain("/assets/landing-hero.webm");
    expect(css).toContain("/assets/hero-video-mask.svg");
    expect(motion).toContain("playbackRate = 0.5");
    expect(motion).toContain("/assets/Logo-white.png");
    expect(css).toContain("font-size: 42px");
  });

  it("contains the longer evidence-led section set", () => {
    const page = readFrontendFile("app/landing/page.tsx");

    for (const sectionId of [
      'id="sources"',
      'id="evidence"',
      'id="human-gates"',
      'id="teams"',
      'id="questions"',
    ]) {
      expect(page).toContain(sectionId);
    }
  });
});

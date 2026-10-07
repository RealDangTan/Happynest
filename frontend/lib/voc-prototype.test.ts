import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const artifactPath = fileURLToPath(
  new URL("../public/happynest-voc-os.html", import.meta.url),
);
const html = existsSync(artifactPath) ? readFileSync(artifactPath, "utf8") : "";

describe("standalone VoC OS prototype", () => {
  it("exists as one self-contained HTML artifact", () => {
    expect(existsSync(artifactPath)).toBe(true);
    expect(html.match(/<main\b/g)?.length).toBe(1);
    expect(html).not.toMatch(/<script[^>]+src=/i);
    expect(html).not.toMatch(/<link[^>]+rel=["']stylesheet/i);
    expect(html).not.toMatch(/\bfetch\s*\(/);
  });

  it("covers the complete product information architecture", () => {
    const requiredViews = [
      "overview",
      "sources",
      "schema",
      "feedback",
      "understand",
      "act",
      "reports",
    ];

    requiredViews.forEach((view) => {
      expect(html).toContain(`data-view="${view}"`);
      expect(html).toContain(`data-nav="${view}"`);
    });
    expect(html).toContain("LISTEN");
    expect(html).toContain("UNDERSTAND");
    expect(html).toContain("ACT");
  });

  it("makes all three human gates and the AI contract explicit", () => {
    ["gate-listen", "gate-understand", "gate-act"].forEach((gate) => {
      expect(html).toContain(`id="${gate}"`);
    });
    expect(html).toContain("Investigate more");
    expect(html).toContain("AI proposes");
    expect(html).toContain("Tools calculate");
    expect(html).toContain("Human governs");
  });

  it("preserves evidence, uncertainty, coverage, and privacy semantics", () => {
    expect(html).toContain("EV-12");
    expect(html).toContain("EV-14");
    expect(html).toContain("EV-18");
    expect(html).toContain("Finding");
    expect(html).toContain("Hypothesis");
    expect(html).toContain("coverage");
    expect(html).toContain("&lt;ORG&gt;");
    expect(html).not.toMatch(/raw_content/i);
  });

  it("exposes deterministic demo controls without an application backend", () => {
    [
      "showView",
      "setStage",
      "startMission",
      "advanceMission",
      "approveGate",
      "runInvestigation",
      "updateAction",
      "openActivity",
    ].forEach((functionName) => expect(html).toContain(functionName));
    expect(html).toContain("100-item cap");
    expect(html).toContain("CSV UTF-8");
  });

  it("includes baseline accessibility and responsive motion contracts", () => {
    expect(html).toContain('<html lang="vi">');
    expect(html).toContain('meta name="viewport"');
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain(":focus-visible");
    expect(html).toContain("@media (max-width:");
    expect(html).toContain("prefers-reduced-motion");
  });
});

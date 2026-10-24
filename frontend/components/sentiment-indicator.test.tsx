import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SentimentIndicator } from "./sentiment-indicator";

describe("sentiment indicators", () => {
  it.each([
    ["positive","Tích cực"], ["negative","Tiêu cực"], ["neutral","Trung lập"],
    ["mixed","Trái chiều"], ["very_positive","Rất tích cực"], ["very neg","Rất tiêu cực"],
  ])("renders %s as an accessible icon with a hover label", (value, label) => {
    const html = renderToStaticMarkup(<SentimentIndicator value={value} />);
    expect(html).toContain("<svg");
    expect(html).toContain(`aria-label="${label}"`);
    expect(html).toContain(`title="${label}"`);
    expect(html).not.toContain(`>${value}<`);
  });
  it("keeps unclassified distinct from neutral", () => {
    const html = renderToStaticMarkup(<SentimentIndicator />);
    expect(html).toContain("Chưa phân loại");
    expect(html).not.toContain("Trung lập");
  });
});

# FE-09 Public Site Design Spec

- Date: 2026-08-30
- Source: browser annotations on `/landing` plus owner request for a longer landing and complete public pages.
- Subject: Happynest, a Vietnamese–English Voice-of-Customer operating system for product and operations teams building AI products.
- Job: explain the LISTEN → UNDERSTAND → ACT loop clearly enough that a visitor can trust the evidence and enter the product.

## Required changes

1. Landing hero fills the viewport below the fixed navigation.
2. Use `/assets/landing-hero.webm` as the hero background, played at `0.5x` after metadata loads.
3. Use `/assets/hero-video-mask.svg` at the hero bottom to create a pixel-ripple transition into the next section.
4. Set the desktop hero headline to 42px while preserving a responsive mobile scale.
5. Replace the navigation bird mark with `/assets/Logo-white.png`; render the `happynest` wordmark in Lora.
6. Extend the landing with specific, credible content about sources, evidence anatomy, human gates, team outcomes, and common questions.
7. Ship public Product, Company, Blog, Docs, Q&A, and Legal routes; all footer and navigation links must resolve without placeholder `#` URLs.
8. Keep anonymous access to all public routes while authenticated users may still visit informational pages.

## Design direction

- Palette: Deep `#0D0E0A`, Charcoal `#171913`, Moss `#2A3021`, Olive `#5F6E44`, Ivory `#F1EDDF`, Gold Mist `#D8C489`.
- Type: Fraunces for editorial display, Inter for reading, Lora for the brand wordmark, Silkscreen for signal labels and evidence metadata.
- Layout: a full-bleed moving field opens into measured editorial bands; evidence cards use stepped rules and compact metadata rather than generic dashboard tiles.
- Signature: the slow hero film dissolves through the supplied irregular pixel mask, turning raw moving feedback into the first structured pipeline section.
- Motion: one ambient hero moment plus existing restrained reveal behavior; all motion respects `prefers-reduced-motion`.

## Self-critique

The inherited near-black/editorial direction can resemble a common AI landing pattern. It stays because the owner explicitly selected it. The revision makes it product-specific through the supplied ripple mask, bilingual feedback examples, evidence lineage, three named human gates, and honest research-prototype language instead of generic SaaS metrics or invented customer claims.


import type { MarketingPage } from "@/lib/marketing-content";
import { lora, silkscreen } from "./fonts";
import { LandingNav, PublicFooter, Reveal } from "./motion";
import "./landing.css";

export function PublicPageShell({ page }: { page: MarketingPage }) {
  return (
    <div className={`${silkscreen.variable} ${lora.variable} hn`}>
      <LandingNav />
      <main>
        <header className="hn-public-hero hn-vignette">
          <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-24 md:py-32 lg:grid-cols-[1fr_0.5fr] lg:items-end">
            <div>
              <p className="hn-eyebrow hn-enter">{page.eyebrow}</p>
              <h1 className="hn-display hn-enter mt-5 max-w-4xl text-4xl font-semibold leading-tight md:text-6xl">
                {page.title}
              </h1>
              <p className="hn-enter mt-6 max-w-2xl text-lg leading-relaxed text-[var(--hn-stone)]">
                {page.description}
              </p>
            </div>
            <nav aria-label={`${page.navLabel} sections`} className="hn-public-index">
              {page.sections.map((section, index) => (
                <a key={section.id} href={`#${section.id}`} className="hn-public-index-link">
                  <span>{(index + 1).toString().padStart(2, "0")}</span>
                  {section.eyebrow}
                </a>
              ))}
            </nav>
          </div>
        </header>

        {page.sections.map((section, index) => (
          <section
            id={section.id}
            key={section.id}
            className={index % 2 === 0 ? "hn-public-section" : "hn-public-section hn-public-section-alt"}
          >
            <div className="mx-auto grid max-w-6xl gap-8 px-4 lg:grid-cols-[0.32fr_1fr]">
              <Reveal>
                <div className="flex items-center gap-4">
                  <span className="hn-public-number">{(index + 1).toString().padStart(2, "0")}</span>
                  <span className="hn-pixel text-[10px] uppercase tracking-widest text-[var(--hn-gold)]">
                    {section.eyebrow}
                  </span>
                </div>
              </Reveal>
              <Reveal delay={90}>
                <article className="max-w-3xl">
                  <h2 className="hn-display text-3xl font-semibold leading-tight md:text-4xl">
                    {section.title}
                  </h2>
                  <p className="mt-6 text-base leading-8 text-[var(--hn-stone)]">
                    {section.body}
                  </p>
                  {section.bullets && (
                    <ul className="hn-public-list mt-8">
                      {section.bullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  )}
                  {section.link && (
                    <a href={section.link.href} className="hn-btn-ghost mt-8">
                      {section.link.label} →
                    </a>
                  )}
                </article>
              </Reveal>
            </div>
          </section>
        ))}

        <section className="hn-public-next">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 py-16 sm:flex-row sm:items-center">
            <div>
              <p className="hn-eyebrow">Continue exploring</p>
              <p className="hn-display mt-3 text-2xl font-semibold">See the operating loop in motion.</p>
            </div>
            <a href="/landing" className="hn-btn">Return to the landing page</a>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}


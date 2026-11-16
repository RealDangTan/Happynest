import type { MarketingPage, MarketingSection } from "@/lib/marketing-content"
import { lora, silkscreen } from "./fonts"
import { FaqList } from "./faq-list"
import { LandingNav, PublicFooter, Reveal } from "./motion"
import { PRODUCT_VISUALS } from "./product-visuals"
import "./landing.css"

/**
 * Bố cục theo loại trang (đợt 3, plan 42):
 * - story  — Product / Company: mỗi mục một dải; Product ghép ảnh giao diện (Intercom).
 * - guide  — Docs / Legal: mục lục dính bên trái để nhảy tới bước cần đọc (Slite, TIDAL).
 * - faq    — Q&A: accordion câu hỏi ngắn (Mixpanel).
 * - notes  — Field notes: lưới bài viết (monday.com blog).
 */
export type PublicLayout = "story" | "guide" | "faq" | "notes"

function SectionBody({ section }: { section: MarketingSection }) {
  return (
    <>
      <p className="mt-6 text-base leading-8 text-[var(--hn-stone)]">{section.body}</p>
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
    </>
  )
}

function StorySections({ page }: { page: MarketingPage }) {
  return (
    <>
      {page.sections.map((section, index) => {
        const Visual = PRODUCT_VISUALS[section.id]
        const withVisual = page.href === "/product" && Visual
        return (
          <section
            id={section.id}
            key={section.id}
            className={index % 2 === 0 ? "hn-public-section" : "hn-public-section hn-public-section-alt"}
          >
            <div className="mx-auto grid max-w-6xl gap-8 px-4 lg:grid-cols-[0.32fr_1fr]">
              <Reveal>
                <div className="flex items-center gap-4">
                  <span className="hn-public-number">{(index + 1).toString().padStart(2, "0")}</span>
                  <span className="hn-pixel text-[10px] tracking-widest text-[var(--hn-gold)] uppercase">
                    {section.eyebrow}
                  </span>
                </div>
              </Reveal>
              <div className={withVisual ? "grid items-start gap-10 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.95fr)]" : undefined}>
                <Reveal delay={90}>
                  <article className="max-w-3xl">
                    <h2 className="hn-display text-3xl leading-tight font-semibold md:text-4xl">{section.title}</h2>
                    <SectionBody section={section} />
                  </article>
                </Reveal>
                {withVisual ? (
                  <Reveal delay={160}>
                    <Visual />
                  </Reveal>
                ) : null}
              </div>
            </div>
          </section>
        )
      })}
    </>
  )
}

function GuideSections({ page }: { page: MarketingPage }) {
  const numbered = page.href === "/docs"
  return (
    <section className="hn-public-section">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <nav aria-label={`${page.navLabel} contents`} className="lg:sticky lg:top-24 lg:self-start">
          <p className="hn-eyebrow mb-3 text-[10px]">On this page</p>
          <ol className="flex flex-col border-l border-[var(--hn-olive)]">
            {page.sections.map((section, index) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="-ml-px flex gap-3 border-l border-transparent py-2 pl-4 text-sm text-[var(--hn-stone)] transition-colors hover:border-[var(--hn-gold)] hover:text-[var(--hn-ivory)]"
                >
                  {numbered ? (
                    <span className="hn-pixel mt-0.5 text-[9px] text-[var(--hn-gold)]">
                      {(index + 1).toString().padStart(2, "0")}
                    </span>
                  ) : null}
                  <span>{section.title}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="flex min-w-0 flex-col">
          {page.sections.map((section) => (
            <article
              key={section.id}
              id={section.id}
              className="scroll-mt-24 border-t border-[var(--hn-olive)] py-12 first:border-t-0 first:pt-0"
            >
              <p className="hn-pixel text-[10px] tracking-widest text-[var(--hn-gold)] uppercase">{section.eyebrow}</p>
              <h2 className="hn-display mt-3 max-w-3xl text-2xl leading-tight font-semibold md:text-3xl">{section.title}</h2>
              <div className="max-w-3xl">
                <SectionBody section={section} />
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function NotesGrid({ page }: { page: MarketingPage }) {
  return (
    <section className="hn-public-section">
      <div className="mx-auto max-w-6xl px-4">
        <ul className="grid gap-5 md:grid-cols-2">
          {page.sections.map((section, index) => (
            <li key={section.id} id={section.id} className="scroll-mt-24">
              <Reveal delay={index * 60}>
                <article className="hn-card flex h-full flex-col p-6 md:p-8">
                  <p className="hn-pixel text-[10px] tracking-widest text-[var(--hn-gold)] uppercase">{section.eyebrow}</p>
                  <h2 className="hn-display mt-4 text-2xl leading-snug font-semibold">{section.title}</h2>
                  <p className="mt-4 flex-1 text-sm leading-7 text-[var(--hn-stone)]">{section.body}</p>
                  {section.link ? (
                    <a href={section.link.href} className="mt-6 self-start text-sm text-[var(--hn-soft)] underline-offset-4 hover:underline">
                      {section.link.label} →
                    </a>
                  ) : null}
                </article>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function PublicPageShell({
  page,
  layout = "story",
}: {
  page: MarketingPage
  layout?: PublicLayout
}) {
  // Mục lục ở hero chỉ cần cho trang dạng câu chuyện; trang hướng dẫn đã có mục
  // lục dính, FAQ và lưới bài viết tự là mục lục.
  const heroIndex = layout === "story"
  return (
    <div className={`${silkscreen.variable} ${lora.variable} hn`}>
      <LandingNav />
      <main>
        <header className="hn-public-hero hn-vignette">
          <div
            className={`relative mx-auto grid max-w-6xl gap-10 px-4 py-24 md:py-32 ${heroIndex ? "lg:grid-cols-[1fr_0.5fr] lg:items-end" : ""}`}
          >
            <div>
              <p className="hn-eyebrow hn-enter">{page.eyebrow}</p>
              <h1 className="hn-display hn-enter mt-5 max-w-4xl text-4xl leading-tight font-semibold md:text-6xl">
                {page.title}
              </h1>
              <p className="hn-enter mt-6 max-w-2xl text-lg leading-relaxed text-[var(--hn-stone)]">
                {page.description}
              </p>
            </div>
            {heroIndex ? (
              <nav aria-label={`${page.navLabel} sections`} className="hn-public-index">
                {page.sections.map((section, index) => (
                  <a key={section.id} href={`#${section.id}`} className="hn-public-index-link">
                    <span>{(index + 1).toString().padStart(2, "0")}</span>
                    {section.eyebrow}
                  </a>
                ))}
              </nav>
            ) : null}
          </div>
        </header>

        {layout === "guide" ? <GuideSections page={page} /> : null}
        {layout === "notes" ? <NotesGrid page={page} /> : null}
        {layout === "faq" ? (
          <section className="hn-public-section">
            <div className="mx-auto max-w-4xl px-4">
              <FaqList sections={page.sections} />
            </div>
          </section>
        ) : null}
        {layout === "story" ? <StorySections page={page} /> : null}

        <section className="hn-public-next">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 py-16 sm:flex-row sm:items-center">
            <div>
              <p className="hn-eyebrow">Continue exploring</p>
              <p className="hn-display mt-3 text-2xl font-semibold">See the operating loop in motion.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <a href="/register" className="hn-btn">
                Create a workspace
              </a>
              <a href="/landing" className="hn-btn-ghost">
                Back to the landing page
              </a>
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  )
}

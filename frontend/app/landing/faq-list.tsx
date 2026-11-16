"use client"
import { useEffect, useRef } from "react"
import type { MarketingSection } from "@/lib/marketing-content"

/**
 * Câu hỏi ngắn dạng accordion (mẫu Mixpanel FAQ). Liên kết sâu `/qna#review`
 * mở đúng câu và cuộn tới nó, vì `<details>` không tự mở theo hash.
 */
export function FaqList({ sections }: { sections: readonly MarketingSection[] }) {
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const openFromHash = () => {
      const id = window.location.hash.slice(1)
      if (!id) return
      const el = listRef.current?.querySelector<HTMLDetailsElement>(`details[id="${CSS.escape(id)}"]`)
      if (!el) return
      el.open = true
      el.scrollIntoView({ block: "start" })
    }
    openFromHash()
    window.addEventListener("hashchange", openFromHash)
    return () => window.removeEventListener("hashchange", openFromHash)
  }, [])

  return (
    <div ref={listRef} className="flex flex-col border-t border-[var(--hn-olive)]">
      {sections.map((section) => (
        <details
          key={section.id}
          id={section.id}
          className="group scroll-mt-24 border-b border-[var(--hn-olive)]"
        >
          <summary className="flex cursor-pointer list-none items-start gap-4 py-6 outline-none [&::-webkit-details-marker]:hidden">
            <span className="hn-pixel mt-1.5 w-24 shrink-0 text-[10px] tracking-widest text-[var(--hn-gold)] uppercase">
              {section.eyebrow}
            </span>
            <span className="hn-display min-w-0 flex-1 text-xl leading-snug font-semibold md:text-2xl">
              {section.title}
            </span>
            <span
              aria-hidden
              className="hn-pixel mt-1 shrink-0 text-lg text-[var(--hn-soft)] transition-transform group-open:rotate-45"
            >
              +
            </span>
          </summary>
          <div className="pb-8 pl-0 md:pl-28">
            <p className="max-w-3xl text-base leading-8 text-[var(--hn-stone)]">{section.body}</p>
            {section.link ? (
              <a href={section.link.href} className="hn-btn-ghost mt-6">
                {section.link.label} →
              </a>
            ) : null}
          </div>
        </details>
      ))}
    </div>
  )
}

import { Badge } from "@/components/ui/badge"
import { parseEvidence } from "@/lib/evidence"
import { cn } from "@/lib/utils"

/**
 * Một bằng chứng của agent, trình bày cho người đọc: bước kiểm tra, điều tìm
 * thấy (tiêu đề + một câu), vài số liệu chính, phân bố dạng thanh và trích dẫn
 * phản hồi. Không lộ JSON, khoá kỹ thuật hay UUID — xem `lib/evidence.ts`.
 * `compact` rút gọn cho danh sách dài (thẻ điều tra, chat).
 */
export function EvidenceCard({
  statement,
  index,
  repeats = 1,
  compact = false,
  className,
}: {
  statement: string
  index?: number
  /** Số lần agent nhận đúng kết quả này (đã gộp trùng). */
  repeats?: number
  compact?: boolean
  className?: string
}) {
  const view = parseEvidence(statement)
  const bars = compact ? view.bars.slice(0, 4) : view.bars
  const quotes = compact ? view.quotes.slice(0, 2) : view.quotes
  const max = Math.max(...bars.map((b) => b.count), 1)

  return (
    <article
      className={cn(
        "flex min-w-0 flex-col gap-2.5 rounded-lg border bg-card p-3 text-sm",
        className,
      )}
    >
      {view.kind || index != null || view.partial || repeats > 1 ? (
        <header className="flex flex-wrap items-center gap-2">
          {index != null ? (
            <span className="font-mono text-[11px] text-muted-foreground">#{index}</span>
          ) : null}
          {view.kind ? <Badge variant="info">{view.kind}</Badge> : null}
          {repeats > 1 ? (
            <span className="text-[11px] text-muted-foreground">
              Kết quả này lặp lại {repeats} lần
            </span>
          ) : null}
          {view.partial ? (
            <span className="text-[11px] text-muted-foreground">Đã rút gọn khi lưu</span>
          ) : null}
        </header>
      ) : null}

      <div className="flex min-w-0 flex-col gap-1">
        {view.title !== view.kind ? (
          <p className={cn("leading-snug break-words", view.kind && "font-medium")}>{view.title}</p>
        ) : null}
        {view.summary ? (
          <p
            className={cn(
              "leading-relaxed break-words",
              view.empty ? "text-muted-foreground" : "text-foreground/85",
            )}
          >
            {view.summary}
          </p>
        ) : null}
      </div>

      {view.facts.length ? (
        <dl className="flex flex-wrap gap-x-5 gap-y-2">
          {view.facts.map((fact) => (
            <div key={fact.label} className="flex min-w-0 flex-col">
              <dt className="text-[11px] text-muted-foreground">{fact.label}</dt>
              <dd className="font-medium break-words">{fact.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {bars.length ? (
        <ul className="flex flex-col gap-1.5" aria-label="Phân bố">
          {bars.map((bar) => (
            <li
              key={bar.label}
              className="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_auto] items-center gap-2"
            >
              <span className="truncate text-xs" title={bar.label}>
                {bar.label}
              </span>
              <span className="h-2 overflow-hidden rounded-full bg-sky-soft" aria-hidden>
                <span
                  className="block h-full rounded-full bg-sky"
                  style={{ width: `${Math.max(4, (bar.count / max) * 100)}%` }}
                />
              </span>
              <span className="text-right font-mono text-xs text-muted-foreground">
                {bar.count}
                <span className="ml-1 text-[10px]">({Math.round(bar.share * 100)}%)</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {quotes.length ? (
        <ul className="flex flex-col gap-2">
          {quotes.map((quote, i) => (
            <li key={i} className="border-l-2 border-sky-line pl-3">
              <p className={cn("leading-relaxed break-words", compact && "line-clamp-3")}>
                “{quote.text}”
              </p>
              {quote.meta ? (
                <p className="text-[11px] text-muted-foreground">{quote.meta}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}

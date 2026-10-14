import type { ReactNode } from "react"

import { usePageTitle } from "@/hooks/use-page-title"

/**
 * Single page-header pattern for every app screen: title (+ optional
 * description) on the left, actions grouped on the right. Stage context
 * ("LISTEN / Importer") already lives in the navbar breadcrumb, so pages
 * must NOT render their own duplicate eyebrow.
 *
 * Tab title: dùng `documentTitle` khi title là ReactNode động; mặc định
 * lấy chính `title` nếu là string.
 */
export function PageHeader({
  title,
  description,
  actions,
  documentTitle,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  documentTitle?: string
}) {
  usePageTitle(documentTitle ?? (typeof title === "string" ? title : undefined))

  return (
    <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
      <div className="flex min-w-0 flex-col gap-1">
        <h1 className="font-heading text-2xl">{title}</h1>
        {description ? (
          <p className="max-w-prose text-sm text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      ) : null}
    </header>
  )
}

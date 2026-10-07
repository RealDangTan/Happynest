import type { ReactNode } from "react";

/**
 * Single page-header pattern for every app screen: title (+ optional
 * description) on the left, actions grouped on the right. Stage context
 * ("LISTEN / Importer") already lives in the navbar breadcrumb, so pages
 * must NOT render their own duplicate eyebrow.
 */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
      <div className="min-w-0 space-y-1">
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
  );
}

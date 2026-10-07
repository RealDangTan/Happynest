"use client";

import { useEffect } from "react";

/** Prod error surface: the default Next error page hides the message — show it. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("global-error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="max-w-md space-y-3 text-center">
          <h1 className="font-heading text-xl">This page couldn&apos;t load</h1>
          <p className="font-mono text-sm text-destructive">{error.message}</p>
          {error.digest ? (
            <p className="font-mono text-xs text-muted-foreground">
              digest {error.digest}
            </p>
          ) : null}
          <div className="flex justify-center gap-2 pt-2">
            <button
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
              onClick={() => reset()}
            >
              Reload
            </button>
            <a
              className="rounded-md border px-3 py-1.5 text-sm"
              href="/importer"
            >
              Back to Importer
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}

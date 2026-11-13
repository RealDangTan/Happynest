"use client";
import { useEffect, useState } from "react";
import { CircleCheck, CircleX, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAgentTrace } from "@/hooks/use-agent";
import { formatElapsed } from "@/lib/investigation";
import { cn } from "@/lib/utils";


/**
 * Live metadata trace for an agent run (HAX G4 "show contextually relevant
 * info" + G16 "disclose AI interaction"): every LLM call the investigation
 * makes, with OK/ERROR, latency, tokens and model. Metadata only — prompts
 * and responses never leave the backend (PII boundary, plan 29).
 */
export function AiTrace({
  runId,
  active,
  startedAt,
  className,
}: {
  runId: string;
  active: boolean;
  startedAt?: string | null;
  className?: string;
}) {
  const trace = useAgentTrace(runId, active);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);

  const items = trace.data?.items ?? [];

  return (
    <div className={cn("rounded-lg border bg-muted/30 p-2", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
          Nhật ký — AI đang làm gì
        </span>
        {active && startedAt ? (
          <span className="font-mono text-[10px] text-muted-foreground">
            đã chạy {formatElapsed(startedAt, now)}
          </span>
        ) : null}
      </div>

      {trace.isError ? (
        <p className="mt-1.5 text-[11px] text-destructive">
          Mất kết nối khi đọc nhật ký — đang tự thử lại.
        </p>
      ) : items.length === 0 ? (
        <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Loader2 className="size-3 animate-spin" /> {active
            ? "AI đang lập kế hoạch điều tra — bước đầu thường mất 20–60 giây…"
            : "Chưa có bước nào được ghi lại."}
        </p>
      ) : (
        <ul className="mt-1.5 flex max-h-64 flex-col gap-1 overflow-y-auto">
          {items.slice(-8).map((row, i) => (
            <li key={i} className="font-mono text-[10.5px] leading-relaxed">
              <span className="inline-flex items-center gap-1">
                {row.status === "error" ? (
                  <CircleX className="size-3 shrink-0 text-destructive" />
                ) : (
                  <CircleCheck className="size-3 shrink-0 text-lichen" />
                )}
                <span className={row.status === "error" ? "text-destructive" : "text-foreground"}>
                  {row.call_type}
                </span>
                <span className="text-muted-foreground">
                  · {row.status === "error" ? "ERROR" : "OK"} · {row.latency_ms}ms
                  {row.prompt_tokens != null && row.completion_tokens != null
                    ? ` · tokens ${row.prompt_tokens}→${row.completion_tokens}`
                    : ""}
                  {` · ${row.model}`}
                </span>
              </span>
              {row.error ? (
                <span className="mt-0.5 block text-destructive">{row.error}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {active ? (
        <p className="mt-1.5 text-[10px] text-muted-foreground">
          Bạn có thể rời màn này — cuộc điều tra vẫn tiếp tục.
        </p>
      ) : null}
      {!active && items.length > 0 ? (
        <div className="mt-1.5 flex items-center gap-1.5">
          <Badge variant="outline" className="text-[9px]">
            {items.filter((r) => r.status === "ok").length} OK
          </Badge>
          {items.some((r) => r.status === "error") ? (
            <Badge variant="destructive" className="text-[9px]">
              {items.filter((r) => r.status === "error").length} failed calls
            </Badge>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

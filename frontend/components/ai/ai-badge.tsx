import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Disclosure badge for AI-generated content (HAX G16): labels what the model
 * produced, with optional provenance (model name / pipeline version).
 */
export function AiBadge({
  model,
  version,
  className,
}: {
  model?: string | null;
  version?: string | null;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-1.5", className)}>
      <Badge variant="outline" className="text-[10px]">
        AI-generated
      </Badge>
      {model ? (
        <span className="font-mono text-[10px] text-muted-foreground">{model}</span>
      ) : null}
      {version ? (
        <span className="font-mono text-[10px] text-muted-foreground">{version}</span>
      ) : null}
    </span>
  );
}

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

/**
 * Chủ đề của một phản hồi dạng tag pill. Mỗi phản hồi mang tới 3 chủ đề
 * (multi-label, xếp theo xác suất giảm dần) nên LUÔN hiện đủ, không chỉ chủ đề
 * đầu. Chưa phân loại → "—"; đã phân loại mà không khớp chủ đề nào → pill
 * "Chưa có chủ đề".
 */
export function TopicPills({
  topics,
  uncategorized,
  label,
  className,
}: {
  topics: string[] | null | undefined
  uncategorized?: boolean
  /** slug → nhãn hiển thị (name_vi của taxonomy) */
  label: (topic: string) => string
  className?: string
}) {
  if (uncategorized) return <Badge variant="outline">Chưa có chủ đề</Badge>
  if (!topics?.length) return <span className="text-muted-foreground">—</span>
  return (
    <ul className={cn("flex flex-wrap gap-1", className)} aria-label="Chủ đề">
      {topics.map((topic) => (
        <li key={topic}>
          <Badge variant="secondary" title={topic} className="max-w-40">
            <span className="truncate">{label(topic)}</span>
          </Badge>
        </li>
      ))}
    </ul>
  )
}

import { cn } from "@/lib/utils"

/**
 * Logo Happynest — biểu tượng ba cánh lá trong `public/assets` (bản màu
 * `Logo-main.png`, bản trắng `Logo-white.png` cho nền ảnh/video tối). Dùng
 * nguyên file của brand, không vẽ lại hay đổi màu.
 */
export function BrandMark({
  className,
  tone = "color",
}: {
  className?: string
  tone?: "color" | "white"
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={tone === "white" ? "/assets/Logo-white.png" : "/assets/Logo-main.png"}
      alt=""
      aria-hidden
      className={cn("size-7 shrink-0 object-contain", className)}
    />
  )
}

import { Fraunces, Inter, JetBrains_Mono } from "next/font/google"
import type { Metadata } from "next"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Providers } from "@/components/providers"
import { Toaster } from "@/components/ui/sonner"
import { cn } from "@/lib/utils"

export const metadata: Metadata = {
  title: {
    default: "Happynest VoC OS",
    template: "%s — Happynest",
  },
  description:
    "AI agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI.",
}

// Brand guideline (UIchart): display serif Fraunces + Inter. Cả ba font nạp
// subset "vietnamese" — Lora/Geist trước đây chỉ có latin nên chữ có dấu bị
// trộn font dự phòng.
const frauncesHeading = Fraunces({
  subsets: ["latin", "vietnamese"],
  variable: "--font-heading",
  axes: ["opsz", "SOFT"],
})

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-sans" })

const fontMono = JetBrains_Mono({
  subsets: ["latin", "vietnamese"],
  variable: "--font-mono",
})

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={cn(
        "antialiased",
        fontMono.variable,
        "font-sans",
        inter.variable,
        frauncesHeading.variable
      )}
    >
      <body>
        <Providers>
          <ThemeProvider>{children}</ThemeProvider>
        </Providers>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  )
}

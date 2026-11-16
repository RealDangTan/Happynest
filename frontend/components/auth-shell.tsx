"use client"
import { useState, type ReactNode } from "react"
import Link from "next/link"
import { ArrowLeft, Eye, EyeOff } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import { GoogleIcon } from "@/components/google-icon"
import { AuthVideoBackground } from "@/components/auth-video-background"
import { LangToggle } from "@/components/lang-toggle"
import { GOOGLE_LOGIN_URL } from "@/lib/google-auth"
import { useAppLang } from "@/lib/i18n"

/**
 * Khung chung cho Đăng nhập / Đăng ký (mẫu Causal + Outseta): một cột form
 * cùng độ rộng, Google là nút viền riêng ở trên, email ở dưới đường chia —
 * hai màn chỉ khác nội dung form, không khác bố cục.
 */
export function AuthShell({
  title,
  description,
  googleLabel,
  dividerLabel,
  children,
  footer,
}: {
  title: string
  description: string
  googleLabel: string
  dividerLabel: string
  children: ReactNode
  footer: ReactNode
}) {
  const lang = useAppLang()
  return (
    <main className="flex min-h-svh items-center justify-center p-4 sm:p-6">
      <AuthVideoBackground />
      <div className="fixed inset-x-4 top-4 z-10 flex items-center justify-between">
        <Button asChild size="sm" variant="ghost" className="bg-background/70 backdrop-blur">
          <Link href="/landing">
            <ArrowLeft data-icon="inline-start" />
            {lang === "vi" ? "Trang chủ" : "Home"}
          </Link>
        </Button>
        <LangToggle className="rounded-lg border bg-background/70 p-1 backdrop-blur" />
      </div>
      <Card className="dark w-full max-w-sm bg-black/90 backdrop-blur-md">
        <CardHeader className="justify-items-center gap-1 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/assets/Logo-white.png" alt="" className="mb-2 size-9" />
          <CardTitle className="font-heading text-xl">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Button
            variant="outline"
            type="button"
            className="h-10 w-full"
            onClick={() => {
              window.location.href = GOOGLE_LOGIN_URL
            }}
          >
            <GoogleIcon data-icon="inline-start" />
            {googleLabel}
          </Button>
          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground">{dividerLabel}</span>
            <Separator className="flex-1" />
          </div>
          {children}
        </CardContent>
        <CardFooter className="justify-center border-t text-sm text-muted-foreground">
          {footer}
        </CardFooter>
      </Card>
    </main>
  )
}

/** Ô mật khẩu có nút hiện/ẩn — giảm gõ sai ở màn đăng ký. */
export function PasswordInput({
  id,
  value,
  onChange,
  autoComplete,
  invalid,
}: {
  id: string
  value: string
  onChange: (value: string) => void
  autoComplete: "current-password" | "new-password"
  invalid?: boolean
}) {
  const lang = useAppLang()
  const [visible, setVisible] = useState(false)
  return (
    <InputGroup>
      <InputGroupInput
        id={id}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        required
        aria-invalid={invalid ? true : undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <InputGroupAddon align="inline-end">
        <InputGroupButton
          size="icon-xs"
          aria-label={visible ? (lang === "vi" ? "Ẩn mật khẩu" : "Hide password") : lang === "vi" ? "Hiện mật khẩu" : "Show password"}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff /> : <Eye />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
  )
}

export function AuthSwitchLink({ prompt, href, label }: { prompt: string; href: string; label: string }) {
  return (
    <p>
      {prompt}{" "}
      <Link href={href} className="text-foreground underline underline-offset-4">
        {label}
      </Link>
    </p>
  )
}

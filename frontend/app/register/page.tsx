"use client"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { CircleAlert, TriangleAlert } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/lib/api"
import { mapAuthError, type AuthAlert } from "@/lib/auth-errors"
import {
  GOOGLE_LOGIN_URL,
  googleErrorAlert,
  useGoogleErrorParam,
} from "@/lib/google-auth"
import { GoogleIcon } from "@/components/google-icon"
import { AuthVideoBackground } from "@/components/auth-video-background"
import { LangToggle } from "@/components/lang-toggle"
import { usePageTitle } from "@/hooks/use-page-title"
import { useAppLang, useT } from "@/lib/i18n"

// Lỗi validate client-side lưu discriminant (không lưu chuỗi) để đổi ngôn ngữ
// vẫn dịch đúng alert đang hiển thị.
type FormError = "password_too_short" | "password_mismatch"

export default function RegisterPage() {
  const t = useT()
  const lang = useAppLang()
  usePageTitle(t.auth.signUp)
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [formError, setFormError] = useState<FormError | null>(null)
  const googleError = useGoogleErrorParam()

  const register = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(15000),
      })
      if (!res.ok) throw await ApiError.from(res)
      return res.json()
    },
    onSuccess: async () => {
      // Đăng ký xong tự đăng nhập luôn — dùng lại OAuth2 password flow.
      // Auto-login hụt thì về /login để người dùng đăng nhập thủ công.
      // Thành công thì dẫn thẳng tới màn onboarding tạo workspace đầu tiên —
      // account mới luôn có workspace TRỐNG thật (isolation 0018).
      const res = await fetch("/api/auth/token", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: email.trim().toLowerCase(),
          password,
        }),
        signal: AbortSignal.timeout(15000),
      })
      router.replace(res.ok ? "/onboarding" : "/login")
      router.refresh()
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (password.length < 8) {
      setFormError("password_too_short")
      return
    }
    if (password !== confirmPassword) {
      setFormError("password_mismatch")
      return
    }
    register.mutate()
  }

  const registerAlert: AuthAlert | null = formError
    ? {
        variant: "warning",
        title: t.auth.invalidDetails,
        description:
          formError === "password_too_short"
            ? t.auth.passwordTooShort
            : t.auth.passwordMismatch,
      }
    : register.error
      ? mapAuthError(register.error, lang)
      : googleErrorAlert(googleError, lang)

  return (
    <main className="flex min-h-svh items-center justify-center p-4 sm:p-6">
      <AuthVideoBackground />
      <div className="fixed right-4 top-4 z-10">
        <LangToggle className="rounded-lg border bg-background/70 p-1 backdrop-blur" />
      </div>
      <Card className="dark w-full max-w-sm bg-black/90 backdrop-blur-md">
        <CardHeader className="justify-items-center gap-1 text-center">
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/assets/Logo-white.png" alt="" className="size-6" />
            <CardTitle>Happynest</CardTitle>
          </div>
          <CardDescription>{t.auth.registerTitle}</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Google OAuth cũng là đăng ký: account chưa có → tạo mới,
              email đã tồn tại → backend tự link/reuse. */}
          <Button
            variant="ghost"
            type="button"
            className="w-full"
            onClick={() => {
              window.location.href = GOOGLE_LOGIN_URL
            }}
          >
            <GoogleIcon data-icon="inline-start" />
            {t.auth.google}
          </Button>
          <div className="my-4 flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground">
              {t.auth.orEmail}
            </span>
            <Separator className="flex-1" />
          </div>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <FieldGroup>
              <Field data-invalid={registerAlert ? true : undefined}>
                <FieldLabel htmlFor="email">{t.auth.email}</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  aria-invalid={registerAlert ? true : undefined}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field data-invalid={registerAlert ? true : undefined}>
                <FieldLabel htmlFor="password">{t.auth.password}</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={registerAlert ? true : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <FieldDescription>{t.auth.passwordHint}</FieldDescription>
              </Field>
              <Field data-invalid={registerAlert ? true : undefined}>
                <FieldLabel htmlFor="confirm-password">
                  {t.auth.confirmPassword}
                </FieldLabel>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={registerAlert ? true : undefined}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </Field>
            </FieldGroup>
            {registerAlert ? (
              <Alert variant={registerAlert.variant}>
                {registerAlert.variant === "destructive" ? (
                  <CircleAlert />
                ) : (
                  <TriangleAlert />
                )}
                <AlertTitle>{registerAlert.title}</AlertTitle>
                <AlertDescription>{registerAlert.description}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={register.isPending}>
              {register.isPending ? <Spinner data-icon="inline-start" /> : null}
              {t.auth.signUp}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {t.auth.haveAccount}{" "}
            <Link
              href="/login"
              className="text-foreground underline underline-offset-4"
            >
              {t.auth.signIn}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}

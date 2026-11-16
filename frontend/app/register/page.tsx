"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { CircleAlert, TriangleAlert } from "lucide-react"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/lib/api"
import { mapAuthError, type AuthAlert } from "@/lib/auth-errors"
import { googleErrorAlert, useGoogleErrorParam } from "@/lib/google-auth"
import { AuthShell, AuthSwitchLink, PasswordInput } from "@/components/auth-shell"
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

  const passwordInvalid = formError != null || Boolean(register.error)

  return (
    // Google OAuth cũng là đăng ký: account chưa có → tạo mới, email đã tồn
    // tại → backend tự link/reuse.
    <AuthShell
      title={t.auth.registerTitle}
      description={lang === "vi" ? "Miễn phí. Bạn tạo workspace ở bước tiếp theo." : "Free. You create your workspace next."}
      googleLabel={t.auth.google}
      dividerLabel={t.auth.orEmail}
      footer={<AuthSwitchLink prompt={t.auth.haveAccount} href="/login" label={t.auth.signIn} />}
    >
      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <FieldGroup>
          <Field data-invalid={register.error ? true : undefined}>
            <FieldLabel htmlFor="email">{t.auth.email}</FieldLabel>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              aria-invalid={register.error ? true : undefined}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field data-invalid={passwordInvalid ? true : undefined}>
            <FieldLabel htmlFor="password">{t.auth.password}</FieldLabel>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              invalid={formError === "password_too_short"}
              value={password}
              onChange={setPassword}
            />
            <FieldDescription>{t.auth.passwordHint}</FieldDescription>
          </Field>
          <Field data-invalid={formError === "password_mismatch" ? true : undefined}>
            <FieldLabel htmlFor="confirm-password">{t.auth.confirmPassword}</FieldLabel>
            <PasswordInput
              id="confirm-password"
              autoComplete="new-password"
              invalid={formError === "password_mismatch"}
              value={confirmPassword}
              onChange={setConfirmPassword}
            />
          </Field>
        </FieldGroup>
        {registerAlert ? (
          <Alert variant={registerAlert.variant}>
            {registerAlert.variant === "destructive" ? <CircleAlert /> : <TriangleAlert />}
            <AlertTitle>{registerAlert.title}</AlertTitle>
            <AlertDescription>{registerAlert.description}</AlertDescription>
          </Alert>
        ) : null}
        <Button type="submit" className="h-10" disabled={register.isPending}>
          {register.isPending ? <Spinner data-icon="inline-start" /> : null}
          {t.auth.signUp}
        </Button>
      </form>
    </AuthShell>
  )
}

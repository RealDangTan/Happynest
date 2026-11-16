"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { CircleAlert, TriangleAlert } from "lucide-react"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/lib/api"
import { mapAuthError } from "@/lib/auth-errors"
import { googleErrorAlert, useGoogleErrorParam } from "@/lib/google-auth"
import { AuthShell, AuthSwitchLink, PasswordInput } from "@/components/auth-shell"
import { usePageTitle } from "@/hooks/use-page-title"
import { useAppLang, useT } from "@/lib/i18n"

export default function LoginPage() {
  const t = useT()
  const lang = useAppLang()
  usePageTitle(t.auth.signIn)
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const googleError = useGoogleErrorParam()

  const login = useMutation({
    mutationFn: async () => {
      // OAuth2 password flow: form-urlencoded, field username (không phải email)
      const body = new URLSearchParams({ username, password })
      const res = await fetch("/api/auth/token", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
        signal: AbortSignal.timeout(15000),
      })
      if (!res.ok) throw await ApiError.from(res)
      return res.json()
    },
    onSuccess: async () => {
      router.replace("/importer")
      router.refresh()
    },
  })

  // Lỗi từ flow Google (?google_error=) hoặc lỗi login email — chung 1 alert.
  const loginAlert =
    login.error
      ? mapAuthError(login.error, lang)
      : googleErrorAlert(googleError, lang)

  return (
    <AuthShell
      title={t.auth.loginTitle}
      description={lang === "vi" ? "Tiếp tục với workspace Happynest của bạn." : "Continue to your Happynest workspace."}
      googleLabel={t.auth.google}
      dividerLabel={t.auth.orEmail}
      footer={<AuthSwitchLink prompt={t.auth.noAccount} href="/register" label={t.auth.signUp} />}
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          login.mutate()
        }}
      >
        <FieldGroup>
          <Field data-invalid={loginAlert ? true : undefined}>
            <FieldLabel htmlFor="username">{t.auth.email}</FieldLabel>
            <Input
              id="username"
              type="email"
              autoComplete="username"
              required
              aria-invalid={loginAlert ? true : undefined}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </Field>
          <Field data-invalid={loginAlert ? true : undefined}>
            <FieldLabel htmlFor="password">{t.auth.password}</FieldLabel>
            <PasswordInput
              id="password"
              autoComplete="current-password"
              invalid={Boolean(loginAlert)}
              value={password}
              onChange={setPassword}
            />
          </Field>
        </FieldGroup>
        {loginAlert ? (
          <Alert variant={loginAlert.variant}>
            {loginAlert.variant === "destructive" ? <CircleAlert /> : <TriangleAlert />}
            <AlertTitle>{loginAlert.title}</AlertTitle>
            <AlertDescription>{loginAlert.description}</AlertDescription>
          </Alert>
        ) : null}
        <Button type="submit" className="h-10" disabled={login.isPending}>
          {login.isPending ? <Spinner data-icon="inline-start" /> : null}
          {t.auth.signIn}
        </Button>
      </form>
    </AuthShell>
  )
}

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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/lib/api"
import { mapAuthError } from "@/lib/auth-errors"
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
          <CardDescription>{t.auth.loginTitle}</CardDescription>
        </CardHeader>
        <CardContent>
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
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  aria-invalid={loginAlert ? true : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
            </FieldGroup>
            {loginAlert ? (
              <Alert variant={loginAlert.variant}>
                {loginAlert.variant === "destructive" ? (
                  <CircleAlert />
                ) : (
                  <TriangleAlert />
                )}
                <AlertTitle>{loginAlert.title}</AlertTitle>
                <AlertDescription>{loginAlert.description}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={login.isPending}>
              {login.isPending ? <Spinner data-icon="inline-start" /> : null}
              {t.auth.signIn}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {t.auth.noAccount}{" "}
            <Link
              href="/register"
              className="text-foreground underline underline-offset-4"
            >
              {t.auth.signUp}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}

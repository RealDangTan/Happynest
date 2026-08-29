"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CircleAlert, TriangleAlert } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import { mapAuthError } from "@/lib/auth-errors";
import { GoogleIcon } from "@/components/google-icon";
import { AuthVideoBackground } from "@/components/auth-video-background";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = useMutation({
    mutationFn: async () => {
      // OAuth2 password flow: form-urlencoded, field username (không phải email)
      const body = new URLSearchParams({ username, password });
      const res = await fetch("/api/auth/token", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
        signal: AbortSignal.timeout(15000),
      });
      if (!res.ok) throw await ApiError.from(res);
      return res.json();
    },
    onSuccess: async () => {
      router.replace("/feedbacks");
      router.refresh();
    },
  });

  const loginAlert = login.error ? mapAuthError(login.error) : null;

  return (
    <main className="flex min-h-svh items-center justify-center p-4 sm:p-6">
      <AuthVideoBackground />
      <Card className="w-full max-w-sm bg-black/90 backdrop-blur-md dark">
        <CardHeader className="justify-items-center gap-1 text-center">
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/assets/Logo-white.png" alt="" className="size-8" />
            <CardTitle>Happynest</CardTitle>
          </div>
          <CardDescription>Đăng nhập để tiếp tục</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="ghost" type="button" className="w-full" disabled title="Sắp có">
            <GoogleIcon data-icon="inline-start" />
            Đăng nhập với Google
          </Button>
          <div className="my-4 flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground">hoặc dùng email</span>
            <Separator className="flex-1" />
          </div>
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              login.mutate();
            }}
          >
            <FieldGroup>
              <Field data-invalid={loginAlert ? true : undefined}>
                <FieldLabel htmlFor="username">Email</FieldLabel>
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
                <FieldLabel htmlFor="password">Mật khẩu</FieldLabel>
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
                {loginAlert.variant === "destructive" ? <CircleAlert /> : <TriangleAlert />}
                <AlertTitle>{loginAlert.title}</AlertTitle>
                <AlertDescription>{loginAlert.description}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={login.isPending}>
              {login.isPending ? <Spinner data-icon="inline-start" /> : null}
              Đăng nhập
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Chưa có tài khoản?{" "}
            <Link href="/register" className="text-foreground underline underline-offset-4">
              Đăng ký
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}

"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import { GoogleIcon } from "@/components/google-icon";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const register = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw await ApiError.from(res);
      return res.json();
    },
    onSuccess: async () => {
      // Đăng ký xong tự đăng nhập luôn — dùng lại OAuth2 password flow.
      await fetch("/api/auth/token", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email.trim().toLowerCase(), password }),
      });
      router.replace("/feedbacks");
      router.refresh();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (password.length < 8) {
      setFormError("Mật khẩu cần ít nhất 8 ký tự.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Mật khẩu xác nhận chưa khớp.");
      return;
    }
    register.mutate();
  }

  const apiErrMsg =
    register.error instanceof ApiError && register.error.status === 409
      ? "Email này đã được đăng ký."
      : String((register.error as ApiError | null)?.message ?? "");
  const errMsg = formError ?? apiErrMsg;

  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Happynest</CardTitle>
          <CardDescription>Tạo tài khoản mới</CardDescription>
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
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <FieldGroup>
              <Field data-invalid={errMsg ? true : undefined}>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  aria-invalid={errMsg ? true : undefined}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field data-invalid={errMsg ? true : undefined}>
                <FieldLabel htmlFor="password">Mật khẩu</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={errMsg ? true : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <FieldDescription>Tối thiểu 8 ký tự.</FieldDescription>
              </Field>
              <Field data-invalid={errMsg ? true : undefined}>
                <FieldLabel htmlFor="confirm-password">Xác nhận mật khẩu</FieldLabel>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={errMsg ? true : undefined}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </Field>
            </FieldGroup>
            {errMsg ? (
              <Alert variant="destructive">
                <AlertTitle>Đăng ký thất bại</AlertTitle>
                <AlertDescription>{errMsg}</AlertDescription>
              </Alert>
            ) : null}
            <Button type="submit" disabled={register.isPending}>
              {register.isPending ? <Spinner data-icon="inline-start" /> : null}
              Đăng ký
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Đã có tài khoản?{" "}
            <Link href="/login" className="text-foreground underline underline-offset-4">
              Đăng nhập
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}

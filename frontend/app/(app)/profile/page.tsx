"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/page-header";
import { DangerRow, SettingsShell } from "@/components/settings/settings-shell";
import { getDisplayUsername, useMe, useUpdateUsername } from "@/hooks/use-me";
import { apiFetch } from "@/lib/api";
import { useT } from "@/lib/i18n";

function InfoRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="w-28 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 wrap-anywhere">{children}</span>
    </div>
  );
}

export default function ProfilePage() {
  const me = useMe();
  const updateUsername = useUpdateUsername();
  const [draftUsername, setDraftUsername] = useState<string | null>(null);
  const router = useRouter();
  const queryClient = useQueryClient();
  const t = useT();

  const logout = useMutation({
    mutationFn: () => apiFetch("/api/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.clear();
      router.replace("/login");
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Không đăng xuất được."),
  });

  if (me.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (me.isError || !me.data) {
    return (
      <SettingsShell>
        <PageHeader title="Hồ sơ" />
        <Alert variant="destructive">
          <AlertTitle>Không tải được thông tin tài khoản</AlertTitle>
          <AlertDescription>
            {me.error instanceof Error
              ? me.error.message
              : "Phiên đăng nhập có thể đã hết."}
          </AlertDescription>
        </Alert>
      </SettingsShell>
    );
  }

  const displayUsername = getDisplayUsername(me.data);
  const initials = displayUsername.slice(0, 2).toUpperCase();
  const username = draftUsername ?? me.data.username ?? "";
  const usernameChanged = username.trim() !== (me.data.username ?? "");

  return (
    <SettingsShell>
      <PageHeader
        title="Hồ sơ"
        description="Tên hiển thị, email và phiên đăng nhập của bạn."
      />

      {/* Dải nhận diện */}
      <Card size="sm">
        <CardContent className="flex-row items-center gap-4">
          <Avatar className="size-14 shrink-0">
            <AvatarFallback className="font-heading text-lg">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="wrap-anywhere font-heading text-lg">{displayUsername}</p>
            <p className="wrap-anywhere text-sm text-muted-foreground">
              {me.data.email}
            </p>

          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tài khoản</CardTitle>
          <CardDescription>
            Mọi tài khoản đăng nhập đều dùng chung workspace và có thể nhập liệu,
            phân tích, duyệt kết quả và quản lý dữ liệu.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <InfoRow label="Email">{me.data.email}</InfoRow>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!usernameChanged || updateUsername.isPending) return;
              updateUsername.mutate(username.trim() || null, {
                onSuccess: () => {
                  setDraftUsername(null);
                  toast.success(t.profile.usernameSaved);
                },
                onError: () => toast.error(t.profile.usernameSaveFailed),
              });
            }}
          >
            <FieldGroup>
              <Field className="@sm/field-group:grid @sm/field-group:grid-cols-[7rem_minmax(0,1fr)]">
                <FieldLabel
                  htmlFor="profile-username"
                  className="font-normal text-muted-foreground @sm/field-group:pt-2"
                >
                  {t.profile.username}
                </FieldLabel>
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <Input
                    id="profile-username"
                    className="min-w-36 max-w-64 flex-1"
                    value={username}
                    placeholder={t.profile.usernamePlaceholder}
                    maxLength={48}
                    disabled={updateUsername.isPending}
                    onChange={(event) => setDraftUsername(event.target.value)}
                  />
                  <Button
                    type="submit"
                    variant="outline"
                    size="sm"
                    disabled={!usernameChanged || updateUsername.isPending}
                  >
                    {updateUsername.isPending && <Spinner data-icon="inline-start" />}
                    {t.profile.usernameSave}
                  </Button>
                </div>
              </Field>
            </FieldGroup>
          </form>
          <InfoRow label="Mật khẩu">
            <Button
              variant="outline"
              size="sm"
              disabled
              title="Sắp có — chưa có endpoint đổi mật khẩu"
            >
              <KeyRound data-icon="inline-start" />
              Đổi mật khẩu
            </Button>
            <span className="ml-2 text-xs text-muted-foreground">Sắp có</span>
          </InfoRow>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Phiên đăng nhập</CardTitle>
          <CardDescription className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-lichen" />
            Hết phiên, hệ thống tự đưa bạn về trang đăng nhập. Đăng xuất chỉ xoá phiên trên trình duyệt này — dữ liệu workspace vẫn giữ nguyên.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DangerRow
            title="Đăng xuất"
            description="Kết thúc phiên trên trình duyệt này."
            action={
              <Button
                variant="outline"
                className="text-destructive hover:text-destructive"
                disabled={logout.isPending}
                onClick={() => logout.mutate()}
              >
                {logout.isPending ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <LogOut data-icon="inline-start" />
                )}
                Đăng xuất
              </Button>
            }
          />
        </CardContent>
      </Card>
    </SettingsShell>
  );
}

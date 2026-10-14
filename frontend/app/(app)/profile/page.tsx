"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
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
import { useMe } from "@/hooks/use-me";
import { apiFetch } from "@/lib/api";

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
      <span className="min-w-0">{children}</span>
    </div>
  );
}

export default function ProfilePage() {
  const me = useMe();
  const router = useRouter();
  const queryClient = useQueryClient();

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
      <div className="flex flex-col gap-6">
        <PageHeader title="Profile" />
        <Alert variant="destructive">
          <AlertTitle>Không tải được thông tin tài khoản</AlertTitle>
          <AlertDescription>
            {me.error instanceof Error
              ? me.error.message
              : "Phiên đăng nhập có thể đã hết."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const initials = me.data.email.slice(0, 2).toUpperCase();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Profile"
        description="Thông tin tài khoản và phiên đăng nhập của bạn trên Happynest."
      />

      {/* Dải nhận diện */}
      <Card size="sm">
        <CardContent className="flex items-center gap-4">
          <Avatar className="size-14">
            <AvatarFallback className="font-heading text-lg">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate font-heading text-lg">{me.data.email}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <code className="truncate font-mono text-xs text-muted-foreground">
                id {me.data.id}
              </code>
            </div>
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
          <CardDescription>
            Phiếu đăng nhập (JWT) nằm trong cookie httpOnly. Hết phiên, mọi lời
            gọi API tự đưa bạn về trang đăng nhập.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-lichen" />
            Đăng xuất trên trình duyệt này chỉ xoá cookie — dữ liệu workspace
            vẫn nguyên trên server.
          </p>
          <Button
            variant="outline"
            className="self-start text-destructive hover:text-destructive"
            disabled={logout.isPending}
            onClick={() => logout.mutate()}
          >
            {logout.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <LogOut data-icon="inline-start" />
            )}
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

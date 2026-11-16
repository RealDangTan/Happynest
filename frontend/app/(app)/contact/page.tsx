"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import { Bug, Info, LifeBuoy, Lightbulb, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/page-header";
import { SettingsShell } from "@/components/settings/settings-shell";
import { useMe } from "@/hooks/use-me";

const TOPICS = [
  { value: "question", label: "Câu hỏi sử dụng" },
  { value: "bug", label: "Báo lỗi" },
  { value: "feature", label: "Đề xuất tính năng" },
  { value: "privacy", label: "Dữ liệu & quyền riêng tư" },
] as const;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ContactPage() {
  const me = useMe();

  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState<string>("");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<{ email?: string; message?: string }>({});
  const [sending, setSending] = useState(false);

  // Prefill email tài khoản khi /api/auth/me trả về sau mount — giữ nguyên
  // nếu user đã tự gõ.
  const accountEmail = me.data?.email;
  useEffect(() => {
    if (accountEmail) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- seed field khi query trả về
      setEmail((cur) => cur || accountEmail);
    }
  }, [accountEmail]);

  const submit = async () => {
    const next: typeof errors = {};
    if (!EMAIL_RE.test(email.trim()))
      next.email = "Email chưa đúng dạng name@domain.";
    if (message.trim().length < 10)
      next.message = `Nội dung cần ít nhất 10 ký tự (hiện ${message.trim().length}).`;
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSending(true);
    // Form demo: chưa có endpoint lưu tin nhắn — mô phỏng độ trễ mạng rồi
    // xác nhận, kèm ghi chú trung thực ngay dưới nút gửi.
    await new Promise((r) => setTimeout(r, 600));
    setSending(false);
    setMessage("");
    toast.success("Đã gửi — cảm ơn phản hồi của bạn!");
  };

  return (
    <SettingsShell>
      <PageHeader
        title="Liên hệ"
        description="Gửi lỗi, đề xuất hay câu hỏi cho nhóm phát triển Happynest."
      />

      {/* Form cạnh cột thông tin (mẫu Aave contact): người gửi biết chọn chủ
          đề nào và điều gì xảy ra sau khi gửi. */}
      <div className="grid min-w-0 items-start gap-6 md:grid-cols-[minmax(0,1fr)_16rem]">
      <Card>
        <CardHeader>
          <CardTitle>Form liên hệ</CardTitle>
          <CardDescription>
            Điền đúng email đang dùng để nhận lời hồi đáp.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="contact-email">Email của bạn</FieldLabel>
              <Input
                id="contact-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                aria-invalid={!!errors.email}
              />
              {errors.email ? (
                <FieldError>{errors.email}</FieldError>
              ) : (
                <FieldDescription>Chỉ dùng để hồi đáp, không lưu.</FieldDescription>
              )}
            </Field>
            <Field>
              <FieldLabel htmlFor="contact-topic">Chủ đề</FieldLabel>
              <Select value={topic} onValueChange={setTopic}>
                <SelectTrigger id="contact-topic" className="w-full">
                  <SelectValue placeholder="Chọn chủ đề" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {TOPICS.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Field data-invalid={!!errors.message || undefined}>
              <FieldLabel htmlFor="contact-message">Nội dung</FieldLabel>
              <Textarea
                id="contact-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Mô tả rõ hiện tượng, màn hình gặp lỗi, hoặc ý tưởng của bạn…"
                rows={5}
                aria-invalid={!!errors.message}
              />
              {errors.message ? (
                <FieldError>{errors.message}</FieldError>
              ) : (
                <FieldDescription>Càng cụ thể càng dễ xử lý.</FieldDescription>
              )}
            </Field>
          </FieldGroup>
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <div className="flex items-center justify-between gap-3">
            <Button onClick={() => void submit()} disabled={sending}>
              {sending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Send data-icon="inline-start" />
              )}
              Gửi phản hồi
            </Button>
          </div>
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <Info className="mt-0.5 size-3.5 shrink-0" />
            Form demo phục vụ luồng UX của bản luận văn — tin nhắn chưa được lưu
            vào backend.
          </p>
        </CardFooter>
      </Card>

      <aside className="flex flex-col gap-4 text-sm">
        <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
          <h2 className="font-medium">Nên chọn chủ đề nào?</h2>
          <ul className="flex flex-col gap-2.5 text-muted-foreground">
            <li className="flex gap-2"><Bug className="mt-0.5 size-4 shrink-0 text-coral-ink" />Báo lỗi: ghi màn hình, thao tác vừa làm và điều bạn thấy.</li>
            <li className="flex gap-2"><Lightbulb className="mt-0.5 size-4 shrink-0 text-sun-ink" />Đề xuất: việc bạn muốn làm được nhưng chưa làm được.</li>
            <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-leaf-ink" />Quyền riêng tư: câu hỏi về dữ liệu và cách ẩn thông tin cá nhân.</li>
          </ul>
        </section>
        <section className="flex flex-col gap-2 rounded-xl border bg-secondary/40 p-4">
          <h2 className="flex items-center gap-2 font-medium">
            <LifeBuoy className="size-4 text-signal" />
            Cần câu trả lời ngay?
          </h2>
          <p className="text-muted-foreground">Phần lớn câu hỏi về nhập file, phân loại và duyệt kết luận đã có trong Trợ giúp.</p>
          <Button asChild size="sm" variant="outline" className="self-start">
            <Link href="/help">Mở Trợ giúp</Link>
          </Button>
        </section>
      </aside>
      </div>
    </SettingsShell>
  );
}

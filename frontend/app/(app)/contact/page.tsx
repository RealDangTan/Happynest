"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Info, Send } from "lucide-react";
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
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Contact"
        description="Gửi phản hồi cho nhóm phát triển Happynest — bug, đề xuất hay câu hỏi đều tiếp."
      />

      <Card className="max-w-xl">
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
    </div>
  );
}

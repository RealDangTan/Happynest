"use client";
import Link from "next/link";
import { ChevronDown, ChevronRight, LifeBuoy } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { STAGES } from "@/lib/navigation";

/** Mô tả từng chặng — cấu trúc trang bám đúng pipeline của đề tài, không phải
 * trang trí: người dùng học cách đi lại của app thông qua chính trang help. */
const STAGE_DESCRIPTIONS: Record<string, string> = {
  LISTEN: "Thu nhận phản hồi thô và chuẩn hoá thành dữ liệu sạch: import CSV, kho feedback và bộ taxonomy.",
  UNDERSTAND:
    "Agent phân cụm, phát hiện vấn đề và đề xuất insight kèm bằng chứng — mọi insight chờ bạn duyệt.",
  ACT: "Ưu tiên hoá thành ma trận và gói thành bản tin hành động cho từng phòng ban.",
};

const FAQS = [
  {
    q: "Nội dung thô của feedback có bị gửi đi đâu không?",
    a: "Không. Mọi feedback đi qua bộ PII sanitizer trước khi vào pipeline: email, số điện thoại, CCCD… được thay bằng placeholder <TYPE>. Nội dung đã sanitize mới là thứ agent thấy trong prompt, log và trace; nội dung thô chỉ nằm trong database.",
  },
  {
    q: "Vì sao chạy analysis xong mà report chưa có insight?",
    a: "Mọi insight đều chờ human review (HITL). Insight ở trạng thái pending phải được bạn duyệt mới tính vào report — nhất là các ca severity critical, có vấn đề an toàn, dính PII hoặc độ tin cậy dưới 0.60.",
  },
  {
    q: "Tài khoản mới có dùng được workspace hiện có không?",
    a: "Có. Mọi tài khoản đăng nhập đều dùng chung workspace, có thể nhập liệu, chạy phân tích, duyệt kết quả và sửa/xoá dữ liệu. Các thao tác xoá vẫn cần xác nhận.",
  },
  {
    q: "Dữ liệu của tôi lưu ở đâu?",
    a: "Trong PostgreSQL (Supabase) kèm vector embedding 1536 chiều cho tìm kiếm ngữ nghĩa. Xoá một workspace là xoá cascade toàn bộ feedback, import, insight và taxonomy của nó trong một transaction.",
  },
];

function FaqItem({ q, a }: { q: string; a: string }) {
  return (
    <details className="group rounded-lg border bg-card open:bg-secondary/40">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">{q}</span>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <p className="border-t px-4 py-3 text-sm leading-relaxed text-muted-foreground">
        {a}
      </p>
    </details>
  );
}

export default function HelpPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Help"
        description="Happynest chạy theo ba chặng cố định — nắm ba chặng là nắm toàn bộ app."
      />

      {/* Ba chặng của pipeline */}
      <div className="grid gap-4 md:grid-cols-3">
        {STAGES.map((stage, i) => (
          <Card key={stage.group} className="gap-3">
            <CardHeader>
              <p className="font-mono text-[11px] uppercase tracking-wider text-signal">
                {String(i + 1).padStart(2, "0")} · {stage.group}
              </p>
              <CardDescription>{STAGE_DESCRIPTIONS[stage.group]}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              {stage.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <item.icon className="size-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">{item.label}</span>
                  <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/50" />
                </Link>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <CardHeader>
            <CardTitle>Câu hỏi thường gặp</CardTitle>
            <CardDescription>
              Bốn điều người mới hay hỏi nhất về dữ liệu và tài khoản.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {FAQS.map((f) => (
              <FaqItem key={f.q} q={f.q} a={f.a} />
            ))}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6">
          <Card size="sm">
            <CardHeader>
              <CardTitle>Phím tắt</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">
                  Tìm kiếm toàn cục
                </span>
                <kbd className="rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  Ctrl K
                </kbd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">
                  Đóng dialog / palette
                </span>
                <kbd className="rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  Esc
                </kbd>
              </div>
            </CardContent>
          </Card>

          <Card size="sm" className="bg-secondary/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LifeBuoy className="size-4 text-signal" />
                Vẫn còn thắc mắc?
              </CardTitle>
              <CardDescription>
                Gửi thẳng cho nhóm phát triển — câu hỏi của bạn giúp app tốt
                lên.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/contact">
                  Mở form liên hệ
                  <ChevronRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

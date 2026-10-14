"use client";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileSpreadsheet,
  LifeBuoy,
  PlayCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { usePageTitle } from "@/hooks/use-page-title";
import { useProduct } from "@/hooks/use-product";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Ba chặng của pipeline — dải tiến trình duy nhất trên trang, nhấn mạnh rằng
 * tạo workspace chỉ là bước 01 của hành trình LISTEN → UNDERSTAND → ACT. */
const STAGE_FLOW = ["LISTEN", "UNDERSTAND", "ACT"] as const;

function StageStrip({ active }: { active: number }) {
  return (
    <ol aria-label="Tiến trình ba chặng" className="flex items-center gap-2">
      {STAGE_FLOW.map((stage, i) => (
        <li key={stage} className="flex items-center gap-2">
          {i > 0 ? (
            <span
              aria-hidden
              className={cn(
                "h-px w-6",
                i <= active ? "bg-lichen/60" : "bg-border",
              )}
            />
          ) : null}
          <span
            className={cn(
              "font-mono text-[10px] uppercase tracking-wider",
              i < active
                ? "text-lichen"
                : i === active
                  ? "text-signal"
                  : "text-muted-foreground/50",
            )}
          >
            {stage}
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Màn onboarding khi tạo workspace đầu tiên — MỘT trang duy nhất: xong bước
 * tạo là chuyển sang trạng thái "next steps" ngay tại chỗ, không wizard nhiều
 * route. Vào được từ: đăng ký xong (redirect), CTA của WelcomeTour, và khi
 * xoá hết workspace từ Workspace settings.
 */
export default function OnboardingPage() {
  usePageTitle("Onboarding");
  const { products, loading, createProduct } = useProduct();
  const [justCreated, setJustCreated] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);

  const hasWorkspace = products.length > 0;
  const done = justCreated ?? products[0]?.name ?? null;

  const handleCreate = async () => {
    if (name.trim().length < 2 || pending) return;
    setPending(true);
    try {
      const created = await createProduct(
        name.trim(),
        description.trim() || undefined,
      );
      setJustCreated(created.name);
      toast.success("Workspace đã tạo — giờ import dữ liệu của bạn.");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Không tạo được workspace.",
      );
    } finally {
      setPending(false);
    }
  };

  const form = (
    <FieldGroup>
      <Field>
        <FieldLabel htmlFor="onboarding-name">Tên workspace</FieldLabel>
        <Input
          id="onboarding-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ví dụ: Chatbot tư vấn sinh viên"
          autoFocus
        />
        <FieldDescription>Một workspace cho một sản phẩm AI.</FieldDescription>
      </Field>
      <Field>
        <FieldLabel htmlFor="onboarding-description">
          Mô tả <span className="text-muted-foreground">(tuỳ chọn)</span>
        </FieldLabel>
        <Input
          id="onboarding-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Sản phẩm này làm gì, cho ai"
        />
      </Field>
    </FieldGroup>
  );

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col justify-center gap-6 py-6">
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-md bg-lichen/20 font-heading text-sm font-semibold text-lichen"
          >
            H
          </span>
          <span className="font-heading text-base">Happynest</span>
          <span className="ml-auto">
            <StageStrip active={done ? 1 : 0} />
          </span>
        </div>
        <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          Setup · 01 / 03 — Listen
        </p>
      </header>

      {loading ? (
        <Card size="sm">
          <CardContent className="flex items-center justify-center py-10">
            <Spinner />
          </CardContent>
        </Card>
      ) : done && !showForm ? (
        /* Trạng thái sau khi workspace tồn tại — của vừa tạo hoặc vào lại trang. */
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="flex size-8 items-center justify-center rounded-full bg-lichen/15 text-lichen"
              >
                <Check className="size-4" />
              </span>
              <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Workspace · 01 ✓
              </p>
            </div>
            <CardTitle className="font-heading text-xl">
              “{done}” đã sẵn sàng
            </CardTitle>
            <CardDescription>
              Hai bước nữa để có insight đầu tiên — cả hai đều có người chấm
              xét (bạn) trước khi tính.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button asChild>
              <Link href="/importer">
                <FileSpreadsheet data-icon="inline-start" />
                Import CSV đầu tiên
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/analysis">
                <PlayCircle data-icon="inline-start" />
                Xem màn Analysis
              </Link>
            </Button>
            {hasWorkspace && !justCreated ? (
              <Button
                variant="ghost"
                size="sm"
                className="justify-start text-muted-foreground"
                onClick={() => setShowForm(true)}
              >
                Tạo workspace khác
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Workspace · 01
            </p>
            <CardTitle className="font-heading text-xl">
              Tạo workspace đầu tiên
            </CardTitle>
            <CardDescription>
              Mọi feedback, import và insight đều gắn với một workspace. Đặt
              tên xong là agent chờ dữ liệu của bạn.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {form}
            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={() => void handleCreate()}
                disabled={name.trim().length < 2 || pending}
              >
                {pending ? <Spinner data-icon="inline-start" /> : null}
                Tạo workspace
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/importer">Để sau — vào thẳng Importer</Link>
              </Button>
            </div>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <LifeBuoy className="size-3.5 shrink-0" />
              Chưa rõ bắt đầu từ đâu?{" "}
              <Link href="/help" className="text-signal underline">
                Xem hướng dẫn ba chặng
              </Link>
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  FileSpreadsheet,
  LifeBuoy,
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
import { BrandMark } from "@/components/brand-mark";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import { STAGES, STAGE_TONE, TONE_CLASSES } from "@/lib/navigation";

/** Ba chặng của pipeline — mỗi chặng mang màu cánh logo như trên sidebar;
 * tạo workspace là bước đầu của chặng Lắng nghe. */
const STAGE_FLOW = ["listen", "understand", "act"] as const;

function StageStrip({ active }: { active: number }) {
  const t = useT();
  return (
    <ol aria-label="Tiến trình ba chặng" className="flex items-center gap-2">
      {STAGE_FLOW.map((stage, i) => (
        <li key={stage} className="flex items-center gap-2">
          {i > 0 ? <span aria-hidden className="h-px w-5 bg-border" /> : null}
          <span
            className={cn(
              "flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider",
              i <= active ? "text-foreground" : "text-muted-foreground",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "size-1.5 rounded-full",
                TONE_CLASSES[STAGE_TONE[stage]].dot,
                i > active && "opacity-40",
              )}
            />
            {t.nav.groups[stage]}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Xem trước workspace sẽ trông thế nào (mẫu Attio "Create workspace"): tên
 * gõ tới đâu hiện tới đó trên một sidebar thu nhỏ với ba chặng thật của app. */
function WorkspacePreview({ name, description }: { name: string; description: string }) {
  const t = useT();
  const label = name.trim() || "Workspace của bạn";
  return (
    <div aria-hidden className="pointer-events-none flex h-full flex-col overflow-hidden rounded-xl border bg-card shadow-sm select-none">
      <div className="flex items-center gap-2 border-b px-3 py-2.5">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-leaf-soft font-heading text-sm text-leaf-ink">
          {label.charAt(0).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className={cn("block truncate text-sm font-medium", !name.trim() && "text-muted-foreground")}>{label}</span>
          <span className="block truncate text-[11px] text-muted-foreground">
            {description.trim() || "Mô tả ngắn sẽ hiện ở đây"}
          </span>
        </span>
      </div>
      <div className="flex flex-1 gap-0">
        <nav className="flex w-40 shrink-0 flex-col gap-3 border-r p-3">
          {STAGES.map((stage) => (
            <div key={stage.group} className="flex flex-col gap-1">
              <span className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                <span className={cn("size-1.5 rounded-full", TONE_CLASSES[STAGE_TONE[stage.group]].dot)} />
                {t.nav.groups[stage.group]}
              </span>
              {stage.items.map((item) => (
                <span key={item.href} className="flex items-center gap-1.5 truncate rounded px-1 py-0.5 text-[11px] text-foreground/80">
                  <item.icon className="size-3 shrink-0 text-muted-foreground" />
                  {t.nav.items[item.key]}
                </span>
              ))}
            </div>
          ))}
        </nav>
        <div className="flex flex-1 flex-col gap-2 p-3">
          <span className="h-3 w-2/3 rounded bg-muted" />
          <span className="h-2 w-1/2 rounded bg-muted/70" />
          <div className="mt-2 flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-3 text-center">
            <FileSpreadsheet className="size-5 text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground">Bước kế tiếp: nhập file phản hồi đầu tiên</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Màn onboarding khi tạo workspace đầu tiên — MỘT trang duy nhất: xong bước
 * tạo là chuyển sang trạng thái "next steps" ngay tại chỗ, không wizard nhiều
 * route. Vào được từ: đăng ký xong (redirect), CTA của WelcomeTour, và khi
 * xoá hết workspace từ Workspace settings.
 */
export default function OnboardingPage() {
  usePageTitle("Tạo workspace");
  const { products, loading, createProduct } = useProduct();
  const router = useRouter();
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
      toast.success("Workspace đã tạo — giờ chọn file phản hồi đầu tiên.");
      // Không dừng ở màn trung gian: tạo xong là sang thẳng bước chọn file.
      router.push("/importer?new=1");
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

  const creating = !loading && !(done && !showForm);

  return (
    <div className={cn("mx-auto flex min-h-[70vh] w-full flex-col justify-center gap-6 py-6", creating ? "max-w-4xl" : "max-w-lg")}>
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <BrandMark />
          <span className="font-heading text-base">Happynest</span>
          <span className="ml-auto">
            <StageStrip active={done ? 1 : 0} />
          </span>
        </div>
        <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          Thiết lập · Lắng nghe
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
                Workspace ✓
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
            <Button asChild size="lg">
              <Link href="/importer?new=1">
                <FileSpreadsheet data-icon="inline-start" />
                Nhập file phản hồi đầu tiên
                <ArrowRight data-icon="inline-end" />
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
        <div className="grid items-stretch gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <Card>
          <CardHeader>
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Workspace
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
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault()
                void handleCreate()
              }}
            >
            {form}
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="submit"
                disabled={name.trim().length < 2 || pending}
              >
                {pending ? <Spinner data-icon="inline-start" /> : null}
                Tạo workspace
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/importer">Để sau</Link>
              </Button>
            </div>
            </form>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <LifeBuoy className="size-3.5 shrink-0" />
              Chưa rõ bắt đầu từ đâu?{" "}
              <Link href="/help" className="text-signal underline">
                Xem hướng dẫn ba chặng
              </Link>
            </p>
          </CardContent>
        </Card>
        <div className="hidden min-h-80 md:block">
          <WorkspacePreview name={name} description={description} />
        </div>
        </div>
      )}
    </div>
  );
}

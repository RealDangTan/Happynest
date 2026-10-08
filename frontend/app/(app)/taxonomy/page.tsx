"use client";

import {
  ArrowRight,
  ListTree,
  Loader2,
  RefreshCcw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useProduct } from "@/hooks/use-product";
import {
  useApplyProposal,
  useApplyRecommendations,
  useGenerateProposal,
  useRecommendTopics,
  useReEnrichUncategorized,
  useTaxonomy,
} from "@/hooks/use-taxonomy";
import {
  displaySlug,
  groupProposalTree,
  groupTaxonomyTree,
  selectedProposalPayload,
} from "@/lib/taxonomy";
import type { ProposedTopic, TopicRecommendation } from "@/lib/types";
import { ApiError } from "@/lib/api";

/** Đổi tên một node trong proposal — cập nhật cả parent của con trỏ tới tên cũ. */
function renameTopic(
  topics: ProposedTopic[],
  oldName: string,
  newName: string,
): ProposedTopic[] {
  const name = newName.trim();
  return topics.map((t) => {
    if (t.name === oldName) return { ...t, name };
    if (t.parent === oldName) return { ...t, parent: name || null };
    return t;
  });
}

export default function TaxonomyPage() {
  const { product, productId } = useProduct();
  const taxonomy = useTaxonomy(productId);
  const generate = useGenerateProposal();
  const applyProposal = useApplyProposal(productId);
  const recommend = useRecommendTopics();
  const applyRecommendations = useApplyRecommendations(productId);
  const reEnrich = useReEnrichUncategorized();

  // Proposal đang review (stateless từ BE — FE giữ draft cho human duyệt).
  const [proposal, setProposal] = useState<ProposedTopic[] | null>(null);
  const [proposalMeta, setProposalMeta] = useState<{
    sampleCount: number;
    model: string;
  } | null>(null);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [form, setForm] = useState({
    product_type: "",
    use_case: "",
    persona: "",
    sample_size: 30,
  });
  const [recommendations, setRecommendations] = useState<
    TopicRecommendation[] | null
  >(null);

  const items = taxonomy.data?.items ?? [];
  const activeItems = items.filter((n) => n.status === "active");
  const tree = groupTaxonomyTree(activeItems);
  const version = product?.taxonomy_version ?? 1;
  const selectedCount =
    proposal?.filter((t) => t.selected !== false).length ?? 0;

  function onGenerate() {
    if (!productId) return;
    generate.mutate(
      {
        product_id: productId,
        sample_size: form.sample_size,
        product_type: form.product_type || null,
        use_case: form.use_case || null,
        persona: form.persona || null,
      },
      {
        onSuccess: (res) => {
          setGenerateOpen(false);
          setProposal(
            res.proposal.topics.map((t) => ({ ...t, selected: true })),
          );
          setProposalMeta({
            sampleCount: res.sample_count,
            model: "GPT",
          });
          toast.success(
            `Đã sinh ${res.proposal.topics.length} chủ đề đề xuất từ ${res.sample_count} mẫu phản hồi.`,
          );
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không sinh được đề xuất — thử lại sau.",
          ),
      },
    );
  }

  function onApplyProposal() {
    if (!proposal) return;
    applyProposal.mutate(
      { topics: selectedProposalPayload(proposal) },
      {
        onSuccess: (res) => {
          setProposal(null);
          setProposalMeta(null);
          toast.success(
            `Đã áp dụng ${res.created.length} chủ đề — Taxonomy v${res.taxonomy_version}.`,
          );
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không áp dụng được đề xuất.",
          ),
      },
    );
  }

  function onRecommend() {
    if (!productId) return;
    recommend.mutate(
      { product_id: productId },
      {
        onSuccess: (res) => {
          if (res.pool_count === 0) {
            toast.info("Chưa có feedback nào chưa phân loại — chạy Analysis trước.");
            return;
          }
          if (res.recommendations.length === 0) {
            toast.info(
              `Đã đọc ${res.pool_count} feedback chưa phân loại — không có chủ đề mới đủ dữ kiện.`,
            );
            return;
          }
          setRecommendations(
            res.recommendations.map((r) => ({ ...r, selected: true })),
          );
          toast.success(
            `GPT đề xuất ${res.recommendations.length} chủ đề từ ${res.pool_count} feedback.`,
          );
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không đọc được pool chưa phân loại.",
          ),
      },
    );
  }

  function onApplyRecommendations() {
    if (!recommendations) return;
    applyRecommendations.mutate(
      recommendations.filter((r) => r.selected !== false),
      {
        onSuccess: (res) => {
          setRecommendations(null);
          toast.success(
            `Đã nhận ${res.created.length} chủ đề — Taxonomy v${res.taxonomy_version}. Bấm "Mở khoá feedback chưa phân loại" để enrich lại theo nhãn mới.`,
          );
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không nhận được chủ đề.",
          ),
      },
    );
  }

  function onReEnrich() {
    if (!productId) return;
    reEnrich.mutate(
      { product_id: productId },
      {
        onSuccess: (res) =>
          toast.success(
            res.released > 0
              ? `Đã mở khoá ${res.released} feedback — sang Feedback Vault bấm Run analysis để enrich lại.`
              : "Không có feedback chưa phân loại nào cần mở khoá.",
          ),
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không mở khoá được feedback.",
          ),
      },
    );
  }

  const busy =
    generate.isPending ||
    applyProposal.isPending ||
    recommend.isPending ||
    applyRecommendations.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Taxonomy"
        description="Bộ nhãn chủ đề cho việc phân loại phản hồi. AI chỉ đề xuất — bạn là người duyệt và áp dụng."
        actions={
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button disabled={!productId || busy}>
                {generate.isPending ? (
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                ) : (
                  <Sparkles data-icon="inline-start" />
                )}
                Sinh đề xuất bằng AI
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Gọi AI sinh đề xuất taxonomy?</AlertDialogTitle>
                <AlertDialogDescription>
                  Sẽ đọc tối đa {form.sample_size} phản hồi đã ẩn danh của sản
                  phẩm{" "}
                  <span className="font-medium text-foreground">
                    {product?.name}
                  </span>{" "}
                  và gọi GPT để đề xuất cây chủ đề — tốn một lần gọi AI nhỏ.
                  Đề xuất chỉ là bản nháp, chưa đổi gì tới taxonomy hiện có.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Xem lại form</AlertDialogCancel>
                <AlertDialogAction onClick={onGenerate}>
                  Gọi AI sinh đề xuất
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        }
      />

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="flex min-w-0 flex-col gap-6">
          {/* ---------------------------------------------- proposal review */}
          {proposal ? (
            <section className="rounded-xl border bg-card px-6 py-6 animate-in fade-in">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <h2 className="font-heading text-lg">
                    Đề xuất từ AI — {proposal.length} chủ đề
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Đọc {proposalMeta?.sampleCount ?? 0} mẫu phản hồi. Bỏ chọn
                    hoặc sửa tên ngay tại chỗ — parent bị bỏ thì con tự nâng
                    lên gốc.
                  </p>
                </div>
                <Badge variant="secondary">bản nháp</Badge>
              </div>
              <Separator className="my-4" />
              <div className="flex flex-col gap-2">
                {groupProposalTree(proposal).map(({ root, children }, rootIdx) => (
                  <div key={`root-${rootIdx}-${root.name}`} className="flex flex-col gap-2">
                    <ProposalRow
                      topic={root}
                      depth={0}
                      onToggle={(selected) =>
                        setProposal((prev) =>
                          (prev ?? []).map((t) =>
                            t === root ? { ...t, selected } : t,
                          ),
                        )
                      }
                      onRename={(name) =>
                        setProposal((prev) => renameTopic(prev ?? [], root.name, name))
                      }
                    />
                    {children.length > 0 ? (
                      <div className="ml-6 flex flex-col gap-2 border-l pl-4">
                        {children.map((child, childIdx) => (
                          <ProposalRow
                            key={`child-${rootIdx}-${childIdx}-${child.name}`}
                            topic={child}
                            depth={1}
                            onToggle={(selected) =>
                              setProposal((prev) =>
                                (prev ?? []).map((t) =>
                                  t === child ? { ...t, selected } : t,
                                ),
                              )
                            }
                            onRename={(name) =>
                              setProposal((prev) =>
                                renameTopic(prev ?? [], child.name, name),
                              )
                            }
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setProposal(null);
                    setProposalMeta(null);
                  }}
                >
                  Bỏ bản nháp
                </Button>
                <Button onClick={onApplyProposal} disabled={applyProposal.isPending || selectedCount === 0}>
                  {applyProposal.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <ListTree data-icon="inline-start" />
                  )}
                  Áp dụng {selectedCount} chủ đề
                </Button>
              </div>
            </section>
          ) : null}

          {/* ---------------------------------------------- active taxonomy */}
          <section className="rounded-xl border bg-card px-6 py-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <h2 className="font-heading text-lg">Taxonomy đang hoạt động</h2>
                <p className="text-sm text-muted-foreground">
                  Nhãn đóng cho engine phân loại. Mỗi chủ đề có slug cố định —
                  đổi tên hiển thị không làm vỡ dữ liệu cũ.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!productId || busy}
                    >
                      {recommend.isPending ? (
                        <Loader2 data-icon="inline-start" className="animate-spin" />
                      ) : (
                        <Sparkles data-icon="inline-start" />
                      )}
                      Đề xuất chủ đề mới
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        Gọi AI đọc feedback chưa phân loại?
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        GPT sẽ đọc các phản hồi chưa phân loại được (hoặc độ tin
                        cậy thấp) và gom lại thành đề xuất chủ đề mới — tốn một
                        lần gọi AI nhỏ. Pool trống thì không tốn gì.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Để sau</AlertDialogCancel>
                      <AlertDialogAction onClick={onRecommend}>
                        Gọi AI đề xuất
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
                <Badge variant="outline">v{version}</Badge>
              </div>
            </div>
            <Separator className="my-4" />
            {taxonomy.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Đang tải…
              </div>
            ) : tree.length === 0 ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <ListTree />
                  </EmptyMedia>
                  <EmptyTitle>Chưa có taxonomy nào</EmptyTitle>
                  <EmptyDescription>
                    Sinh đề xuất bằng AI từ chính phản hồi của sản phẩm, rồi
                    duyệt và áp dụng — hoặc nhập thử vài feedback trước để AI
                    có dữ kiện.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <div className="flex flex-col gap-2">
                {tree.map(({ node, children }) => (
                  <div key={node.id} className="flex flex-col gap-1.5">
                    <TaxonomyRow node={node} depth={0} />
                    {children.length > 0 ? (
                      <div className="ml-6 flex flex-col gap-1.5 border-l pl-4">
                        {children.map((child) => (
                          <TaxonomyRow key={child.id} node={child} depth={1} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ------------------------------------------- recommendations */}
          {recommendations ? (
            <section className="rounded-xl border bg-card px-6 py-6 animate-in fade-in">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <h2 className="font-heading text-lg">
                    Chủ đề đề xuất mới — {recommendations.length}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    GPT gom từ các phản hồi chưa phân loại được. Ví dụ là trích
                    nguyên văn (đã ẩn danh).
                  </p>
                </div>
                <Badge variant="secondary">chờ bạn duyệt</Badge>
              </div>
              <Separator className="my-4" />
              <div className="flex flex-col gap-3">
                {recommendations.map((rec) => (
                  <label
                    key={rec.name}
                    className="flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors hover:bg-accent/40"
                  >
                    <Checkbox
                      className="mt-0.5"
                      checked={rec.selected !== false}
                      onCheckedChange={(checked) =>
                        setRecommendations((prev) =>
                          (prev ?? []).map((r) =>
                            r === rec ? { ...r, selected: checked === true } : r,
                          ),
                        )
                      }
                    />
                    <span className="flex min-w-0 flex-col gap-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{rec.name}</span>
                        <Badge variant="outline">
                          {rec.evidence_count} phản hồi
                        </Badge>
                        {rec.parent ? (
                          <Badge variant="secondary">trong “{rec.parent}”</Badge>
                        ) : null}
                      </span>
                      {rec.examples.length > 0 ? (
                        <span className="flex flex-col gap-0.5 text-sm text-muted-foreground">
                          {rec.examples.map((ex) => (
                            <span key={ex} className="line-clamp-1 italic">
                              “{ex}”
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </span>
                  </label>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-end gap-2">
                <Button variant="ghost" onClick={() => setRecommendations(null)}>
                  Bỏ
                </Button>
                <Button
                  onClick={onApplyRecommendations}
                  disabled={
                    applyRecommendations.isPending ||
                    recommendations.every((r) => r.selected === false)
                  }
                >
                  {applyRecommendations.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <ListTree data-icon="inline-start" />
                  )}
                  Nhận{" "}
                  {recommendations.filter((r) => r.selected !== false).length}{" "}
                  chủ đề
                </Button>
              </div>
            </section>
          ) : null}
        </div>

        {/* ------------------------------------------------------- aside */}
        <aside className="flex flex-col gap-6">
          <section className="rounded-xl border bg-card px-5 py-5">
            <h3 className="font-heading text-base">Vòng lặp taxonomy</h3>
            <ol className="mt-3 flex list-decimal flex-col gap-2 pl-5 text-sm text-muted-foreground">
              <li>Nhập phản hồi tại Importer / Vault.</li>
              <li>Sinh đề xuất — AI học từ chính phản hồi thật.</li>
              <li>Duyệt &amp; áp dụng — chỉ bạn thay đổi bộ nhãn.</li>
              <li>Phản hồi chưa phân loại sẽ được GPT đọc lại để đề xuất chủ đề mới.</li>
            </ol>
            <Separator className="my-4" />
            <p className="text-sm text-muted-foreground">
              Sau khi nhận chủ đề mới, mở khoá các phản hồi chưa phân loại để
              chạy lại phân tích theo nhãn mới.
            </p>
            <Button
              variant="outline"
              className="mt-3 w-full"
              onClick={onReEnrich}
              disabled={!productId || reEnrich.isPending}
            >
              {reEnrich.isPending ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <RefreshCcw data-icon="inline-start" />
              )}
              Mở khoá feedback chưa phân loại
            </Button>
            <Button asChild variant="ghost" className="mt-2 w-full">
              <Link href="/vault">
                Sang Feedback Vault
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          </section>

          <section className="rounded-xl border bg-card px-5 py-5">
            <h3 className="font-heading text-base">Sinh đề xuất từ bối cảnh</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Bối cảnh giúp GPT đặt tên chủ đề đúng ngôn ngữ ngành của bạn.
            </p>
            <Button variant="outline" className="mt-3 w-full" onClick={() => setGenerateOpen(true)}>
              Mở form bối cảnh
            </Button>
          </section>
        </aside>
      </div>

      {/* ------------------------------------------------ generate dialog */}
      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bối cảnh cho GPT</DialogTitle>
            <DialogDescription>
              Không bắt buộc — nhưng mô tả càng rõ, tên chủ đề càng sát ngành.
              AI chỉ đọc phản hồi đã ẩn danh.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="tax-product-type">Loại sản phẩm</FieldLabel>
              <Input
                id="tax-product-type"
                placeholder="VD: chatbot CSKH, app ví điện tử"
                value={form.product_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, product_type: e.target.value }))
                }
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="tax-use-case">Use case chính</FieldLabel>
              <Input
                id="tax-use-case"
                placeholder="VD: trả lời câu hỏi về đơn hàng và hoàn tiền"
                value={form.use_case}
                onChange={(e) =>
                  setForm((f) => ({ ...f, use_case: e.target.value }))
                }
              />
              <FieldDescription>Mô tả ngắn một dòng là đủ.</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="tax-persona">Người dùng điển hình</FieldLabel>
              <Input
                id="tax-persona"
                placeholder="VD: chủ shop online nhỏ, dùng điện thoại"
                value={form.persona}
                onChange={(e) =>
                  setForm((f) => ({ ...f, persona: e.target.value }))
                }
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="tax-sample-size">Số mẫu phản hồi đọc</FieldLabel>
              <Input
                id="tax-sample-size"
                type="number"
                min={1}
                max={50}
                value={form.sample_size}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    sample_size: Number(e.target.value) || 30,
                  }))
                }
              />
              <FieldDescription>Nhiều mẫu hơn → đề xuất phủ hơn, hơi tốn token hơn.</FieldDescription>
            </Field>
          </FieldGroup>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setGenerateOpen(false)}>
              Đóng
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button disabled={generate.isPending || !productId}>
                  {generate.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <Sparkles data-icon="inline-start" />
                  )}
                  Sinh đề xuất
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Gọi AI sinh đề xuất?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Đọc tối đa {form.sample_size} phản hồi của{" "}
                    <span className="font-medium text-foreground">
                      {product?.name}
                    </span>{" "}
                    và gọi GPT — tốn một lần gọi AI nhỏ. Kết quả là bản nháp,
                    bạn duyệt xong mới áp dụng.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Để xem lại</AlertDialogCancel>
                  <AlertDialogAction onClick={onGenerate}>
                    Gọi AI
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ProposalRow({
  topic,
  depth,
  onToggle,
  onRename,
}: {
  topic: ProposedTopic;
  depth: number;
  onToggle: (selected: boolean) => void;
  onRename: (name: string) => void;
}) {
  const selected = topic.selected !== false;
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors ${
        selected ? "bg-background" : "bg-muted/40 opacity-60"
      }`}
    >
      <Checkbox
        checked={selected}
        onCheckedChange={(checked) => onToggle(checked === true)}
        aria-label={`Chọn chủ đề ${topic.name}`}
      />
      <Input
        className="h-7 flex-1 border-transparent bg-transparent px-2 text-sm font-medium shadow-none hover:border-input focus-visible:bg-background"
        value={topic.name}
        onChange={(e) => onRename(e.target.value)}
        aria-label={`Tên chủ đề (cấp ${depth + 1})`}
      />
      {topic.description ? (
        <span className="hidden max-w-48 truncate text-xs text-muted-foreground md:block">
          {topic.description}
        </span>
      ) : null}
    </div>
  );
}

function TaxonomyRow({ node, depth }: { node: { name: string; slug: string | null; kind: string }; depth: number }) {
  return (
    <div
      className={`flex flex-wrap items-center gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-accent/40 ${
        depth > 0 ? "text-sm" : "font-medium"
      }`}
    >
      <span>{node.name}</span>
      <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
        {displaySlug(node.slug)}
      </code>
      {node.kind === "emerging" ? (
        <Badge variant="secondary">emerging</Badge>
      ) : null}
    </div>
  );
}

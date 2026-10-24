"use client"

import {
  ArrowRight,
  Copy,
  ListTree,
  Loader2,
  Pencil,
  Plus,
  RefreshCcw,
  Sparkles,
  Trash2,
} from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/page-header"
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
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useProduct } from "@/hooks/use-product"
import {
  useApplyProposal,
  useApplyRecommendations,
  useCreateTaxonomyNode,
  useDeleteTaxonomyNode,
  useGenerateProposal,
  useRecommendTopics,
  useReEnrichUncategorized,
  useTaxonomy,
  useUpdateTaxonomyNode,
} from "@/hooks/use-taxonomy"
import {
  groupProposalTree,
  groupTaxonomyTree,
  selectedProposalPayload,
} from "@/lib/taxonomy"
import type { ProposedTopic, TaxonomyNode, TopicRecommendation } from "@/lib/types"
import { ApiError } from "@/lib/api"
import { cn } from "@/lib/utils"

/** Đổi tên canonical (EN) một node trong proposal — cập nhật cả parent của con
 * trỏ tới tên cũ (parent khớp theo NAME tiếng Anh). */
function renameTopic(
  topics: ProposedTopic[],
  oldName: string,
  newName: string
): ProposedTopic[] {
  const name = newName.trim()
  return topics.map((t) => {
    if (t.name === oldName) return { ...t, name }
    if (t.parent === oldName) return { ...t, parent: name || null }
    return t
  })
}

export default function TaxonomyPage() {
  const { product, productId } = useProduct()
  const taxonomy = useTaxonomy(productId)
  const generate = useGenerateProposal()
  const applyProposal = useApplyProposal(productId)
  const recommend = useRecommendTopics()
  const applyRecommendations = useApplyRecommendations(productId)
  const reEnrich = useReEnrichUncategorized()

  // Proposal đang review (stateless từ BE — FE giữ draft cho human duyệt).
  const [proposal, setProposal] = useState<ProposedTopic[] | null>(null)
  const [proposalMeta, setProposalMeta] = useState<{
    sampleCount: number
    model: string
  } | null>(null)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [form, setForm] = useState({
    product_type: "",
    use_case: "",
    persona: "",
    sample_size: 30,
  })
  const [recommendations, setRecommendations] = useState<
    TopicRecommendation[] | null
  >(null)

  // ----------------------------------------------------- manual CRUD state
  const createNode = useCreateTaxonomyNode(productId)
  const updateNode = useUpdateTaxonomyNode(productId)
  const deleteNode = useDeleteTaxonomyNode(productId)
  const [addOpen, setAddOpen] = useState(false)
  const [addForm, setAddForm] = useState({
    name: "",
    name_vi: "",
    parent_slug: "__root__",
    description: "",
  })
  const [editTarget, setEditTarget] = useState<TaxonomyNode | null>(null)
  const [editForm, setEditForm] = useState({
    name: "",
    name_vi: "",
    description: "",
  })
  const [deleteTarget, setDeleteTarget] = useState<TaxonomyNode | null>(null)

  function onAddNode() {
    if (!productId) return
    createNode.mutate(
      {
        name: addForm.name,
        name_vi: addForm.name_vi.trim() ? addForm.name_vi.trim() : null,
        parent_slug: addForm.parent_slug === "__root__" ? null : addForm.parent_slug,
        description: addForm.description.trim() ? addForm.description.trim() : null,
      },
      {
        onSuccess: (node) => {
          setAddOpen(false)
          setAddForm({ name: "", name_vi: "", parent_slug: "__root__", description: "" })
          toast.success(`Đã thêm “${node.name_vi ?? node.name}” vào bộ nhãn.`)
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không thêm được chủ đề."
          ),
      }
    )
  }

  function onOpenEdit(node: TaxonomyNode) {
    setEditTarget(node)
    setEditForm({
      name: node.name,
      name_vi: node.name_vi ?? "",
      description: node.description ?? "",
    })
  }

  function onSaveEdit() {
    if (!editTarget) return
    updateNode.mutate(
      {
        slug: editTarget.slug ?? "",
        name: editForm.name,
        name_vi: editForm.name_vi.trim() ? editForm.name_vi.trim() : editForm.name,
        description: editForm.description.trim() ? editForm.description.trim() : null,
      },
      {
        onSuccess: (node) => {
          setEditTarget(null)
          toast.success(
            `Đã lưu “${node.name_vi ?? node.name}” — dữ liệu đã phân loại không bị ảnh hưởng.`
          )
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không lưu được chủ đề."
          ),
      }
    )
  }

  function onDeleteNode() {
    if (!deleteTarget?.slug) return
    deleteNode.mutate(deleteTarget.slug, {
      onSuccess: () => {
        toast.success(
          `Đã xóa “${deleteTarget.name}” khỏi bộ nhãn. Feedback đã phân loại giữ nguyên nhãn cũ.`
        )
        setDeleteTarget(null)
      },
      onError: (err) =>
        toast.error(
          err instanceof ApiError ? err.message : "Không xóa được chủ đề."
        ),
    })
  }

  const items = taxonomy.data?.items ?? []
  const activeItems = items.filter((n) => n.status === "active")
  const tree = groupTaxonomyTree(activeItems)
  const version = product?.taxonomy_version ?? 1
  const selectedCount =
    proposal?.filter((t) => t.selected !== false).length ?? 0

  function onGenerate() {
    if (!productId) return
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
          setGenerateOpen(false)
          setProposal(
            res.proposal.topics.map((t) => ({ ...t, selected: true }))
          )
          setProposalMeta({
            sampleCount: res.sample_count,
            model: "GPT",
          })
          toast.success(
            `Đã sinh ${res.proposal.topics.length} chủ đề đề xuất từ ${res.sample_count} mẫu phản hồi.`
          )
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không sinh được đề xuất — thử lại sau."
          ),
      }
    )
  }

  function onApplyProposal() {
    if (!proposal) return
    applyProposal.mutate(
      { topics: selectedProposalPayload(proposal) },
      {
        onSuccess: (res) => {
          setProposal(null)
          setProposalMeta(null)
          toast.success(
            `Đã áp dụng ${res.created.length} chủ đề — Taxonomy v${res.taxonomy_version}.`
          )
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không áp dụng được đề xuất."
          ),
      }
    )
  }

  function onRecommend() {
    if (!productId) return
    recommend.mutate(
      { product_id: productId },
      {
        onSuccess: (res) => {
          if (res.pool_count === 0) {
            toast.info(
              "Chưa có feedback nào chưa phân loại — chạy Analysis trước."
            )
            return
          }
          if (res.recommendations.length === 0) {
            toast.info(
              `Đã đọc ${res.pool_count} feedback chưa phân loại — không có chủ đề mới đủ dữ kiện.`
            )
            return
          }
          setRecommendations(
            res.recommendations.map((r) => ({ ...r, selected: true }))
          )
          toast.success(
            `GPT đề xuất ${res.recommendations.length} chủ đề từ ${res.pool_count} feedback.`
          )
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không đọc được pool chưa phân loại."
          ),
      }
    )
  }

  function onApplyRecommendations() {
    if (!recommendations) return
    applyRecommendations.mutate(
      recommendations.filter((r) => r.selected !== false),
      {
        onSuccess: (res) => {
          setRecommendations(null)
          toast.success(
            `Đã nhận ${res.created.length} chủ đề — Taxonomy v${res.taxonomy_version}. Bấm "Mở khoá feedback chưa phân loại" để enrich lại theo nhãn mới.`
          )
        },
        onError: (err) =>
          toast.error(
            err instanceof ApiError ? err.message : "Không nhận được chủ đề."
          ),
      }
    )
  }

  function onReEnrich() {
    if (!productId) return
    reEnrich.mutate(
      { product_id: productId },
      {
        onSuccess: (res) =>
          toast.success(
            res.released > 0
              ? `Đã mở khoá ${res.released} feedback — sang Feedback Vault bấm "Analyze pending items" để chạy lại.`
              : "Không có feedback chưa phân loại nào cần mở khoá."
          ),
        onError: (err) =>
          toast.error(
            err instanceof ApiError
              ? err.message
              : "Không mở khoá được feedback."
          ),
      }
    )
  }

  const busy =
    generate.isPending ||
    applyProposal.isPending ||
    recommend.isPending ||
    applyRecommendations.isPending

  return (
    <div className="flex flex-col gap-6">
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
                <AlertDialogTitle>
                  Gọi AI sinh đề xuất taxonomy?
                </AlertDialogTitle>
                <AlertDialogDescription>
                  Sẽ đọc tối đa {form.sample_size} phản hồi đã ẩn danh của sản
                  phẩm{" "}
                  <span className="font-medium text-foreground">
                    {product?.name}
                  </span>{" "}
                  và gọi GPT để đề xuất cây chủ đề — tốn một lần gọi AI nhỏ. Mẫu
                  được lấy phân tầng theo thời gian và gộp trùng lặp nên không
                  lệch về giai đoạn gần đây. Đề xuất chỉ là bản nháp, chưa đổi gì
                  tới taxonomy hiện có.
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
            <Card className="animate-in fade-in">
              <CardHeader>
                <CardTitle>Đề xuất từ AI — {proposal.length} chủ đề</CardTitle>
                <CardDescription>
                  Đọc {proposalMeta?.sampleCount ?? 0} mẫu phản hồi. Bỏ chọn
                  hoặc sửa tên ngay tại chỗ — parent bị bỏ thì con tự nâng lên
                  gốc.
                </CardDescription>
                <CardAction>
                  <Badge variant="secondary">bản nháp</Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {groupProposalTree(proposal).map(
                  ({ root, children }, rootIdx) => (
                    <div
                      key={`root-${rootIdx}-${root.name}`}
                      className="flex flex-col gap-2"
                    >
                      <ProposalRow
                        topic={root}
                        depth={0}
                        onToggle={(selected) =>
                          setProposal((prev) =>
                            (prev ?? []).map((t) =>
                              t === root ? { ...t, selected } : t
                            )
                          )
                        }
                        onRename={(name) =>
                          setProposal((prev) =>
                            renameTopic(prev ?? [], root.name, name)
                          )
                        }
                        onRenameVi={(name_vi) =>
                          setProposal((prev) =>
                            (prev ?? []).map((t) =>
                              t === root ? { ...t, name_vi } : t
                            )
                          )
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
                                    t === child ? { ...t, selected } : t
                                  )
                                )
                              }
                              onRename={(name) =>
                                setProposal((prev) =>
                                  renameTopic(prev ?? [], child.name, name)
                                )
                              }
                              onRenameVi={(name_vi) =>
                                setProposal((prev) =>
                                  (prev ?? []).map((t) =>
                                    t === child ? { ...t, name_vi } : t
                                  )
                                )
                              }
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )
                )}
              </CardContent>
              <CardFooter className="justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setProposal(null)
                    setProposalMeta(null)
                  }}
                >
                  Bỏ bản nháp
                </Button>
                <Button
                  onClick={onApplyProposal}
                  disabled={applyProposal.isPending || selectedCount === 0}
                >
                  {applyProposal.isPending ? (
                    <Loader2
                      data-icon="inline-start"
                      className="animate-spin"
                    />
                  ) : (
                    <ListTree data-icon="inline-start" />
                  )}
                  Áp dụng {selectedCount} chủ đề
                </Button>
              </CardFooter>
            </Card>
          ) : null}

          {/* ---------------------------------------------- active taxonomy */}
          <Card>
            <CardHeader>
              <CardTitle>Taxonomy đang hoạt động</CardTitle>
              <CardDescription>
                Nhãn đóng cho engine phân loại. Mỗi chủ đề có slug cố định — đổi
                tên hiển thị không làm vỡ dữ liệu cũ.
              </CardDescription>
              <CardAction className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!productId || busy}
                  onClick={() => {
                    setAddForm({ name: "", name_vi: "", parent_slug: "__root__", description: "" })
                    setAddOpen(true)
                  }}
                >
                  <Plus data-icon="inline-start" />
                  Thêm chủ đề
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!productId || busy}
                    >
                      {recommend.isPending ? (
                        <Loader2
                          data-icon="inline-start"
                          className="animate-spin"
                        />
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
              </CardAction>
            </CardHeader>
            <CardContent>
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
                      <TaxonomyRow
                        node={node}
                        depth={0}
                        onEdit={onOpenEdit}
                        onDelete={setDeleteTarget}
                      />
                      {children.length > 0 ? (
                        <div className="ml-6 flex flex-col gap-1.5 border-l pl-4">
                          {children.map((child) => (
                            <TaxonomyRow
                              key={child.id}
                              node={child}
                              depth={1}
                              onEdit={onOpenEdit}
                              onDelete={setDeleteTarget}
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* ------------------------------------------- recommendations */}
          {recommendations ? (
            <Card className="animate-in fade-in">
              <CardHeader>
                <CardTitle>
                  Chủ đề đề xuất mới — {recommendations.length}
                </CardTitle>
                <CardDescription>
                  GPT gom từ các phản hồi chưa phân loại được. Ví dụ là trích
                  nguyên văn (đã ẩn danh).
                </CardDescription>
                <CardAction>
                  <Badge variant="secondary">chờ bạn duyệt</Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
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
                            r === rec ? { ...r, selected: checked === true } : r
                          )
                        )
                      }
                    />
                    <span className="flex min-w-0 flex-col gap-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">
                          {rec.name_vi ?? rec.name}
                        </span>
                        {rec.name !== (rec.name_vi ?? rec.name) ? (
                          <span className="font-mono text-xs text-muted-foreground">
                            {rec.name}
                          </span>
                        ) : null}
                        <Badge variant="outline">
                          {rec.evidence_count} phản hồi
                        </Badge>
                        {rec.parent ? (
                          <Badge variant="secondary">
                            trong “{rec.parent}”
                          </Badge>
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
              </CardContent>
              <CardFooter className="justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => setRecommendations(null)}
                >
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
                    <Loader2
                      data-icon="inline-start"
                      className="animate-spin"
                    />
                  ) : (
                    <ListTree data-icon="inline-start" />
                  )}
                  Nhận{" "}
                  {recommendations.filter((r) => r.selected !== false).length}{" "}
                  chủ đề
                </Button>
              </CardFooter>
            </Card>
          ) : null}
        </div>

        {/* ------------------------------------------------------- aside */}
        <aside className="flex flex-col gap-6">
          <Card size="sm">
            <CardHeader>
              <CardTitle>Vòng lặp taxonomy</CardTitle>
            </CardHeader>
            <CardContent className="gap-3">
              <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm text-muted-foreground">
                <li>Nhập phản hồi tại Importer / Vault.</li>
                <li>Sinh đề xuất — AI học từ chính phản hồi thật.</li>
                <li>Duyệt &amp; áp dụng — chỉ bạn thay đổi bộ nhãn.</li>
                <li>
                  Phản hồi chưa phân loại sẽ được GPT đọc lại để đề xuất chủ đề
                  mới.
                </li>
              </ol>
              <p className="text-sm text-muted-foreground">
                Sau khi nhận chủ đề mới, mở khoá các phản hồi chưa phân loại để
                chạy lại phân tích theo nhãn mới.
              </p>
            </CardContent>
            <CardFooter className="flex-col items-stretch gap-2">
              <Button
                variant="outline"
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
              <Button asChild variant="ghost">
                <Link href="/vault">
                  Sang Feedback Vault
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          <Card size="sm">
            <CardHeader>
              <CardTitle>Sinh đề xuất từ bối cảnh</CardTitle>
              <CardDescription>
                Tùy chọn — giúp GPT đặt tên chủ đề đúng ngành; bỏ trống thì AI
                tự suy luận từ phản hồi.
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setGenerateOpen(true)}
              >
                Mở form bối cảnh
              </Button>
            </CardFooter>
          </Card>
        </aside>
      </div>

      {/* ------------------------------------------------ generate dialog */}
      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bối cảnh cho GPT</DialogTitle>
            <DialogDescription>
              Không bắt buộc — bỏ trống thì AI tự suy luận loại sản phẩm từ
              chính phản hồi. Mô tả càng rõ, tên chủ đề càng sát ngành. AI chỉ
              đọc phản hồi đã ẩn danh.
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
              <FieldLabel htmlFor="tax-persona">
                Người dùng điển hình
              </FieldLabel>
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
              <FieldLabel htmlFor="tax-sample-size">
                Số mẫu phản hồi đọc
              </FieldLabel>
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
              <FieldDescription>
                Mẫu phân tầng đều theo thời gian — nhiều mẫu hơn giúp phủ rộng
                hơn, hơi tốn token hơn.
              </FieldDescription>
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
                    <Loader2
                      data-icon="inline-start"
                      className="animate-spin"
                    />
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

      {/* ------------------------------------------------- add node dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-h-[min(85dvh,640px)] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Thêm chủ đề mới</DialogTitle>
            <DialogDescription>
              Chủ đề vào ngay bộ nhãn đóng cho engine phân loại. Slug tự sinh từ
              tên (bỏ dấu) và không đổi về sau.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="node-name">Tên tiếng Anh (canonical)</FieldLabel>
              <Input
                id="node-name"
                placeholder="VD: Note Sync"
                value={addForm.name}
                onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
              />
              <FieldDescription>
                Danh từ/cụm danh từ tiếng Anh chỉ mảng hoặc tính năng — nhãn chuẩn
                cho engine phân loại, không chứa đánh giá hay mức độ (cái đó thuộc
                sentiment/severity).
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="node-name-vi">Tên hiển thị tiếng Việt</FieldLabel>
              <Input
                id="node-name-vi"
                placeholder="VD: Đồng bộ ghi chú"
                value={addForm.name_vi}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, name_vi: e.target.value }))
                }
              />
              <FieldDescription>
                Nhãn hiện trên UI cho người dùng. Bỏ trống → dùng tên tiếng Anh.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="node-parent">Chủ đề cha</FieldLabel>
              <Select
                value={addForm.parent_slug}
                onValueChange={(value) => setAddForm((f) => ({ ...f, parent_slug: value }))}
              >
                <SelectTrigger id="node-parent" className="w-full">
                  <SelectValue placeholder="Chọn cấp" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="__root__">Gốc (không có cha)</SelectItem>
                    {activeItems
                      .filter((n) => n.slug)
                      .map((n) => (
                        <SelectItem key={n.id} value={n.slug as string}>
                          {n.name_vi ?? n.name}
                        </SelectItem>
                      ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="node-description">Mô tả (tùy chọn)</FieldLabel>
              <Textarea
                id="node-description"
                rows={2}
                placeholder="Tiêu chí cái gì thuộc / không thuộc chủ đề này."
                value={addForm.description}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, description: e.target.value }))
                }
              />
              <FieldDescription>
                Giúp AI đặt tên chủ đề đúng ngữ cảnh khi sinh đề xuất.
              </FieldDescription>
            </Field>
          </FieldGroup>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setAddOpen(false)}>
              Đóng
            </Button>
            <Button
              onClick={onAddNode}
              disabled={!productId || createNode.isPending || !addForm.name.trim()}
            >
              {createNode.isPending ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Plus data-icon="inline-start" />
              )}
              Thêm chủ đề
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------ edit node dialog */}
      <Dialog
        open={editTarget != null}
        onOpenChange={(open) => {
          if (!open) setEditTarget(null)
        }}
      >
        <DialogContent className="max-h-[min(85dvh,640px)] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Sửa chủ đề</DialogTitle>
            <DialogDescription>
              Chỉ đổi tên hiển thị / mô tả — mã định danh nội bộ của chủ đề giữ
              nguyên nên dữ liệu đã phân loại không vỡ.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel>Tag lưu trong DB</FieldLabel>
              <div className="flex items-center gap-2">
                <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1.5 font-mono text-xs text-muted-foreground">
                  {editTarget?.slug ?? "—"}
                </code>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Copy tag"
                  disabled={!editTarget?.slug}
                  onClick={() => {
                    if (!editTarget?.slug) return
                    void navigator.clipboard
                      .writeText(editTarget.slug)
                      .then(() => toast.success(`Đã copy tag “${editTarget.slug}”.`))
                      .catch(() => toast.error("Không copy được — trình duyệt chặn clipboard."))
                  }}
                >
                  <Copy />
                </Button>
              </div>
              <FieldDescription>
                Giá trị nằm trong <code className="font-mono">ai_analysis.topics</code> của
                feedback — cố định, không đổi được khi rename.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="edit-node-name">Tên tiếng Anh (canonical)</FieldLabel>
              <Input
                id="edit-node-name"
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
              />
              <FieldDescription>
                Nhãn chuẩn cho engine phân loại — đổi tên không đổi slug nên dữ
                liệu cũ không vỡ.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="edit-node-name-vi">
                Tên hiển thị tiếng Việt
              </FieldLabel>
              <Input
                id="edit-node-name-vi"
                value={editForm.name_vi}
                placeholder={editForm.name}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, name_vi: e.target.value }))
                }
              />
              <FieldDescription>
                Nhãn hiện trên UI. Bỏ trống → dùng tên tiếng Anh.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="edit-node-description">Mô tả</FieldLabel>
              <Textarea
                id="edit-node-description"
                rows={2}
                value={editForm.description}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, description: e.target.value }))
                }
              />
              <FieldDescription>Để trống là xóa mô tả.</FieldDescription>
            </Field>
          </FieldGroup>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setEditTarget(null)}>
              Đóng
            </Button>
            <Button
              onClick={onSaveEdit}
              disabled={updateNode.isPending || !editForm.name.trim()}
            >
              {updateNode.isPending ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Pencil data-icon="inline-start" />
              )}
              Lưu thay đổi
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* --------------------------------------------- delete confirm dialog */}
      <AlertDialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Xóa “{deleteTarget?.name_vi ?? deleteTarget?.name}”?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Chủ đề bị gỡ khỏi bộ nhãn đóng — các run phân tích tương lai không
              còn dùng nó. Feedback ĐÃ phân loại giữ nguyên nhãn cũ nên dữ liệu
              không mất. Chủ đề còn chủ đề con thì phải xóa con trước.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
            <AlertDialogAction
              className="text-destructive"
              onClick={(event) => {
                event.preventDefault()
                onDeleteNode()
              }}
            >
              {deleteNode.isPending ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Trash2 data-icon="inline-start" />
              )}
              Xóa chủ đề
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function ProposalRow({
  topic,
  depth,
  onToggle,
  onRename,
  onRenameVi,
}: {
  topic: ProposedTopic
  depth: number
  onToggle: (selected: boolean) => void
  onRename: (name: string) => void
  onRenameVi: (name_vi: string) => void
}) {
  const selected = topic.selected !== false
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors ${
        selected ? "bg-background" : "bg-muted/40 opacity-60"
      }`}
    >
      <Checkbox
        checked={selected}
        onCheckedChange={(checked) => onToggle(checked === true)}
        aria-label={`Chọn chủ đề ${topic.name_vi ?? topic.name}`}
      />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <Input
          className="h-7 border-transparent bg-transparent px-2 text-sm font-medium shadow-none hover:border-input focus-visible:bg-background"
          value={topic.name_vi ?? ""}
          placeholder={topic.name}
          onChange={(e) => onRenameVi(e.target.value)}
          aria-label={`Tên hiển thị tiếng Việt (cấp ${depth + 1})`}
        />
        <Input
          className="h-5 border-transparent bg-transparent px-2 font-mono text-xs text-muted-foreground shadow-none hover:border-input focus-visible:bg-background"
          value={topic.name}
          onChange={(e) => onRename(e.target.value)}
          aria-label={`Tên tiếng Anh canonical (cấp ${depth + 1})`}
        />
      </div>
      {topic.description ? (
        <span className="hidden max-w-48 truncate text-xs text-muted-foreground md:block">
          {topic.description}
        </span>
      ) : null}
    </div>
  )
}

function TaxonomyRow({
  node,
  depth,
  onEdit,
  onDelete,
}: {
  node: TaxonomyNode
  depth: number
  onEdit: (node: TaxonomyNode) => void
  onDelete: (node: TaxonomyNode) => void
}) {
  return (
    <div
      className={cn(
        "group/row flex flex-wrap items-center gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-accent/40",
        depth > 0 ? "text-sm" : "font-medium"
      )}
    >
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="cursor-default underline decoration-dotted decoration-border underline-offset-4">
              {node.name_vi ?? node.name}
            </span>
          </TooltipTrigger>
          <TooltipContent>
            Lưu trong DB:{" "}
            <span className="font-mono">{node.slug ?? "—"}</span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      {node.name !== (node.name_vi ?? node.name) ? (
        <span className="hidden font-mono text-xs text-muted-foreground lg:block">
          {node.name}
        </span>
      ) : null}
      {node.description ? (
        <span className="hidden max-w-64 truncate text-xs text-muted-foreground lg:block">
          {node.description}
        </span>
      ) : null}
      {node.kind === "emerging" ? (
        <Badge variant="secondary">emerging</Badge>
      ) : null}
      <span className="ml-auto flex items-center gap-0.5 opacity-0 transition-opacity group-hover/row:opacity-100 focus-within:opacity-100">
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={`Sửa chủ đề ${node.name_vi ?? node.name}`}
          onClick={() => onEdit(node)}
        >
          <Pencil />
        </Button>
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={`Xóa chủ đề ${node.name_vi ?? node.name}`}
          className="text-destructive hover:text-destructive"
          onClick={() => onDelete(node)}
        >
          <Trash2 />
        </Button>
      </span>
    </div>
  )
}

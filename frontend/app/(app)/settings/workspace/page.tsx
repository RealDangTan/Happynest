"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { AlertTriangle, Check, Plus, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/page-header";
import { usePageTitle } from "@/hooks/use-page-title";
import { useProduct } from "@/hooks/use-product";
import {
  useDeleteProduct,
  useUpdateProduct,
} from "@/hooks/use-products";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function WorkspaceSettingsPage() {
  usePageTitle("Workspace settings");
  const router = useRouter();
  const { products, product, productId, setProductId, createProduct, loading } =
    useProduct();
  const update = useUpdateProduct();
  const deleteProduct = useDeleteProduct();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  // Seed form mỗi lần đổi workspace active (mẫu của SettingsDialog cũ).
  useEffect(() => {
    if (product) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- seed lại form khi đổi workspace
      setName(product.name);
      setDescription(product.description ?? "");
    }
  }, [product?.id]); // eslint-disable-line react-hooks/exhaustive-deps -- chỉ seed khi ĐỔI workspace, không ghi đè khi user đang gõ

  const dirty =
    !!product &&
    (name.trim() !== product.name ||
      description.trim() !== (product.description ?? ""));

  const save = () => {
    if (!product || name.trim().length < 2) return;
    update.mutate(
      {
        id: product.id,
        body: { name: name.trim(), description: description.trim() || null },
      },
      {
        onSuccess: () => toast.success("Đã lưu thay đổi workspace."),
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Không lưu được thay đổi.",
          ),
      },
    );
  };

  const handleCreate = async () => {
    if (newName.trim().length < 2) return;
    try {
      const created = await createProduct(
        newName.trim(),
        newDescription.trim() || undefined,
      );
      setCreateOpen(false);
      setNewName("");
      setNewDescription("");
      toast.success(`Đã tạo và chuyển sang “${created.name}”.`);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Không tạo được workspace.",
      );
    }
  };

  const handleDelete = () => {
    if (!product || deleteConfirmText !== product.name) return;
    deleteProduct.mutate(product.id, {
      onSuccess: ({ deleted_counts }) => {
        const total = Object.values(deleted_counts).reduce((a, b) => a + b, 0);
        toast.success(`Đã xoá workspace và ${total} bản ghi liên quan.`);
        setDeleteOpen(false);
        setDeleteConfirmText("");
        const next = products.find((p) => p.id !== product.id);
        if (next) {
          setProductId(next.id);
        } else {
          // Hết workspace → quay lại đúng màn onboarding tạo workspace đầu tiên.
          router.push("/onboarding");
        }
      },
      onError: (err) =>
        toast.error(err instanceof Error ? err.message : "Không xoá được."),
    });
  };

  if (!loading && products.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Workspace settings"
          description="Danh tính product dùng chung toàn workspace."
        />
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>Chưa có workspace nào</EmptyTitle>
            <EmptyDescription>
              Tạo workspace đầu tiên để bắt đầu thu thập phản hồi.
            </EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link href="/onboarding">Tạo workspace đầu tiên</Link>
          </Button>
        </Empty>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Workspace settings"
        description="Danh tính product dùng chung toàn workspace — đổi ở đây là đổi mọi màn hình."
        actions={
          product ? (
            <Button variant="outline" onClick={() => setCreateOpen(true)}>
              <Plus data-icon="inline-start" />
              Workspace mới
            </Button>
          ) : null
        }
      />

      {loading || !product ? (
        <Card size="sm">
          <CardContent className="flex items-center justify-center py-10">
            <Spinner />
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Thông tin chung</CardTitle>
              <CardDescription>
                Tên và mô tả hiện trong breadcrumb, báo cáo và bản tin phòng
                ban.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="ws-name">Tên workspace</FieldLabel>
                  <Input
                    id="ws-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="ws-description">Mô tả</FieldLabel>
                  <Input
                    id="ws-description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Sản phẩm này làm gì (tuỳ chọn)"
                  />
                  <FieldDescription>
                    Trùng tên workspace đã có sẽ bị từ chối (409).
                  </FieldDescription>
                </Field>
              </FieldGroup>
            </CardContent>
            <CardFooter className="justify-end gap-2">
              <Button
                variant="outline"
                disabled={!dirty}
                onClick={() => {
                  if (product) {
                    setName(product.name);
                    setDescription(product.description ?? "");
                  }
                }}
              >
                Hoàn tác
              </Button>
              <Button
                onClick={save}
                disabled={!dirty || name.trim().length < 2 || update.isPending}
              >
                {update.isPending ? <Spinner data-icon="inline-start" /> : null}
                Lưu thay đổi
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Chuyển workspace</CardTitle>
              <CardDescription>
                Workspace đang mở là {product.name}. Danh sách chỉ gồm workspace
                bạn owns.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              {products.map((p) => (
                <button
                  key={p.id}
                  onClick={() => {
                    if (p.id !== productId) {
                      setProductId(p.id);
                      toast.success(`Đã chuyển sang “${p.name}”.`);
                    }
                  }}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                    p.id === productId
                      ? "bg-accent font-medium"
                      : "hover:bg-accent/60"
                  }`}
                >
                  <span
                    aria-hidden
                    className={
                      p.id === productId
                        ? "text-lichen"
                        : "text-transparent"
                    }
                  >
                    <Check className="size-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{p.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      Tạo {formatDate(p.created_at)}
                    </span>
                  </span>
                  {p.id === productId ? (
                    <Badge variant="secondary">Đang mở</Badge>
                  ) : null}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card size="sm">
            <CardHeader>
              <CardTitle>Chi tiết kỹ thuật</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              <div className="flex items-center gap-3">
                <span className="w-32 shrink-0 text-muted-foreground">
                  Product ID
                </span>
                <code className="truncate font-mono text-xs">{product.id}</code>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-32 shrink-0 text-muted-foreground">
                  Tạo lúc
                </span>
                <span>{formatDate(product.created_at)}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-32 shrink-0 text-muted-foreground">
                  Taxonomy
                </span>
                <span>
                  version{" "}
                  <Badge variant="outline" className="font-mono">
                    v{product.taxonomy_version ?? 0}
                  </Badge>
                </span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-destructive/40">
            <CardHeader>
              <CardTitle className="text-destructive">Danger zone</CardTitle>
              <CardDescription>
                Xoá workspace xoá cứng toàn bộ feedback, import, insight và
                taxonomy của nó khỏi database — không có undo.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                onClick={() => {
                  setDeleteConfirmText("");
                  setDeleteOpen(true);
                }}
              >
                <Trash2 data-icon="inline-start" />
                Xoá “{product.name}”…
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {/* Tạo workspace mới — cùng hợp đồng với dialog trên breadcrumb */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Workspace mới</DialogTitle>
            <DialogDescription>
              Workspace mới bắt đầu trống — Importer là màn hình đầu tiên.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="ws-new-name">Tên</FieldLabel>
              <Input
                id="ws-new-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Demo AI"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="ws-new-description">Mô tả</FieldLabel>
              <Input
                id="ws-new-description"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Sản phẩm này làm gì (tuỳ chọn)"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Huỷ
            </Button>
            <Button
              onClick={() => void handleCreate()}
              disabled={newName.trim().length < 2}
            >
              Tạo workspace
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Xoá workspace — bắt buộc gõ đúng tên, cùng hợp đồng với breadcrumb */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Xoá “{product?.name}” vĩnh viễn?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ feedback, import, insight và schema của workspace này sẽ
              bị xoá khỏi database và không thể hoàn tác. Gõ đúng tên để xác
              nhận.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Field>
            <FieldLabel htmlFor="ws-delete-confirm">
              Gõ “{product?.name}” để xác nhận
            </FieldLabel>
            <Input
              id="ws-delete-confirm"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder={product?.name}
              autoComplete="off"
            />
          </Field>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={
                !product ||
                deleteConfirmText !== product.name ||
                deleteProduct.isPending
              }
              onClick={(e) => {
                e.preventDefault();
                handleDelete();
              }}
            >
              {deleteProduct.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <AlertTriangle data-icon="inline-start" />
              )}
              Xoá vĩnh viễn
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Check,
  ChevronsUpDown,
  Menu,
  PanelLeftOpen,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { useProduct } from "@/hooks/use-product";
import {
  useCreateProduct,
  useDeleteProduct,
  useUpdateProduct,
} from "@/hooks/use-products";
import { toast } from "sonner";
import { usePanel } from "./panel-provider";
import { useChat } from "./chat-provider";
import { ProfilePanel } from "./profile-panel";
import { ActivityNavButton } from "@/components/activity/activity-nav-button";
import { WhatsNew } from "./whats-new";
import { CommandPalette } from "./command-palette";
import { findStage } from "@/lib/navigation";
import { cn } from "@/lib/utils";

/** Breadcrumb: Happynest ▸ product ▸ stage ▸ screen (product doubles as switcher). */
function Breadcrumb() {
  const { products, product, setProductId } = useProduct();
  const { chatOpen } = useChat();
  const router = useRouter();
  const pathname = usePathname();
  const stage = findStage(pathname);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const createProduct = useCreateProduct();

  const updateProduct = useUpdateProduct();
  const deleteProduct = useDeleteProduct();
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameName, setRenameName] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const handleRename = () => {
    if (!product || renameName.trim().length < 2) return;
    updateProduct.mutate(
      { id: product.id, body: { name: renameName.trim() } },
      {
        onSuccess: () => {
          toast.success("Product updated.");
          setRenameOpen(false);
        },
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Could not rename product",
          ),
      },
    );
  };

  const handleDelete = () => {
    if (!product || deleteConfirmText !== product.name) return;
    deleteProduct.mutate(product.id, {
      onSuccess: ({ deleted_counts }) => {
        const total = Object.values(deleted_counts).reduce((a, b) => a + b, 0);
        toast.success(
          `Đã xoá product và ${total} bản ghi liên quan khỏi database.`,
        );
        setDeleteOpen(false);
        setDeleteConfirmText("");
        const next = products.find((p) => p.id !== product.id);
        if (next) setProductId(next.id);
        router.push("/importer");
      },
      onError: (err) =>
        toast.error(
          err instanceof Error ? err.message : "Không xoá được product.",
        ),
    });
  };

  const handleSelect = (id: string) => {
    setProductId(id);
    const saved = localStorage.getItem(`happynest.last-screen.${id}`);
    router.push(saved ?? "/importer");
  };

  const handleCreate = async () => {
    if (name.trim().length < 2) return;
    try {
      await createProduct.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setOpen(false);
      setName("");
      setDescription("");
      router.push("/importer");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create product");
    }
  };

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 text-sm">
      <DropdownMenu>
        <DropdownMenuTrigger
          className="flex min-w-0 items-center gap-1 rounded-md px-1.5 py-1 font-medium outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Switch product"
        >
          <span className="max-w-40 truncate">{product?.name ?? "Choose a product"}</span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel>Choose a product</DropdownMenuLabel>
          {products.map((p) => (
            <DropdownMenuItem key={p.id} onSelect={() => handleSelect(p.id)}>
              <Check
                data-icon="inline-start"
                className={p.id === product?.id ? "opacity-100" : "opacity-0"}
              />
              <span className="min-w-0 flex-1 truncate">{p.name}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setOpen(true)}>
            <Plus data-icon="inline-start" />
            Create product
          </DropdownMenuItem>
          {product ? (
            <>
              <DropdownMenuItem
                onSelect={() => {
                  setRenameName(product.name);
                  setRenameOpen(true);
                }}
              >
                <Pencil data-icon="inline-start" />
                Rename product
              </DropdownMenuItem>
              <DropdownMenuItem
                variant="destructive"
                onSelect={() => {
                  setDeleteConfirmText("");
                  setDeleteOpen(true);
                }}
              >
                <Trash2 data-icon="inline-start" />
                Delete product…
              </DropdownMenuItem>
            </>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>

      {!chatOpen && stage.group ? (
        <>
          <span className="text-muted-foreground/60" aria-hidden>
            /
          </span>
          <span className="rounded-full bg-signal/10 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide text-signal">
            {stage.group}
          </span>
          <span className="text-muted-foreground/60" aria-hidden>
            /
          </span>
          <span className="truncate text-muted-foreground">{stage.label}</span>
        </>
      ) : chatOpen ? (
        <>
          <span className="text-muted-foreground/60" aria-hidden>
            /
          </span>
          <span className="rounded-full bg-signal/10 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide text-signal">
            CHAT
          </span>
        </>
      ) : null}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create product</DialogTitle>
            <DialogDescription>
              A new product starts empty — the Importer is the first screen.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="crumb-product-name">Name</FieldLabel>
              <Input
                id="crumb-product-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Demo AI"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="crumb-product-description">Description</FieldLabel>
              <Input
                id="crumb-product-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this product does (optional)"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void handleCreate()} disabled={name.trim().length < 2}>
              Create product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename product (pm) */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename product</DialogTitle>
            <DialogDescription>
              Tên mới áp dụng cho toàn bộ workspace này.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="rename-product-name">Product name</FieldLabel>
              <Input
                id="rename-product-name"
                value={renameName}
                onChange={(e) => setRenameName(e.target.value)}
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRename}
              disabled={renameName.trim().length < 2 || updateProduct.isPending}
            >
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete product (pm) — typed confirmation */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete “{product?.name}”?</DialogTitle>
            <DialogDescription>
              Toàn bộ feedback, import, insight và schema của product này sẽ bị xoá
              vĩnh viễn khỏi database (không thể hoàn tác). Gõ đúng tên product để
              xác nhận.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="delete-product-confirm">
                Gõ “{product?.name}” để xác nhận
              </FieldLabel>
              <Input
                id="delete-product-confirm"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder={product?.name}
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={
                !product ||
                deleteConfirmText !== product.name ||
                deleteProduct.isPending
              }
            >
              <Trash2 data-icon="inline-start" />
              Delete permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </nav>
  );
}

export function TopNavbar() {
  const { collapsed, setCollapsed, mobileOpen, setMobileOpen } = usePanel();
  const { chatOpen } = useChat();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { productId } = useProduct();

  // Ctrl/Cmd + K opens the global palette; "/" also works when not typing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-30 h-14 border-b bg-card/80 backdrop-blur transition-[left] duration-200",
        chatOpen ? "md:left-80" : collapsed ? "md:left-14" : "md:left-64",
      )}
    >
      <div className="flex h-full items-center gap-2 px-3 md:px-4">
        <button
          className="rounded-md p-1.5 hover:bg-accent outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </button>
        {collapsed ? (
          <button
            className="hidden rounded-md p-1.5 hover:bg-accent outline-none focus-visible:ring-2 focus-visible:ring-ring md:block"
            onClick={() => setCollapsed(false)}
            aria-label="Expand panel"
            title="Expand panel"
          >
            <PanelLeftOpen className="size-4" />
          </button>
        ) : null}

        <Breadcrumb />

        <div className="ml-auto flex items-center gap-1">
          {/* search trigger */}
          <button
            onClick={() => setPaletteOpen(true)}
            className={cn(
              "flex h-8 items-center gap-2 rounded-md border bg-background/60 px-2.5 text-sm text-muted-foreground outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring",
              "w-9 justify-center lg:w-44 lg:justify-start",
            )}
            aria-label="Search (Ctrl K)"
          >
            <Search className="size-4 shrink-0" />
            <span className="hidden lg:inline">Search…</span>
            <kbd className="ml-auto hidden rounded border bg-secondary px-1.5 py-0.5 font-mono text-[10px] xl:inline">
              Ctrl K
            </kbd>
          </button>

          <ActivityNavButton />

          <div className="hidden lg:block">
            <WhatsNew />
          </div>

          <div className="hidden md:block">
            <ProfilePanel />
          </div>
        </div>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} productId={productId} />
    </header>
  );
}

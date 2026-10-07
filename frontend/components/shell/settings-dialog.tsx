"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { useProduct } from "@/hooks/use-product";
import { useUpdateProduct } from "@/hooks/use-products";

export function SettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { product } = useProduct();
  const update = useUpdateProduct();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (open && product) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- seed fields each time the dialog opens
      setName(product.name);
      setDescription(product.description ?? "");
    }
  }, [open, product]);

  const save = () => {
    if (!product || name.trim().length < 2) return;
    update.mutate(
      {
        id: product.id,
        body: { name: name.trim(), description: description.trim() || null },
      },
      {
        onSuccess: () => {
          toast.success("Product updated.");
          onOpenChange(false);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Could not update product"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Product identity used across the workspace.</DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="settings-name">Product name</FieldLabel>
            <Input
              id="settings-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="settings-description">Description</FieldLabel>
            <Input
              id="settings-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this product does (optional)"
            />
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={name.trim().length < 2 || update.isPending}>
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

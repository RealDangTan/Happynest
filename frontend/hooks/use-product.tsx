"use client";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useProducts, useCreateProduct } from "@/hooks/use-products";
import type { Product } from "@/lib/types";

const STORAGE_KEY = "happynest.active-product";

type ProductContextValue = {
  products: Product[];
  product: Product | null;
  productId: string | null;
  setProductId: (id: string) => void;
  createProduct: (name: string, description?: string) => Promise<Product>;
  loading: boolean;
};

const ProductContext = createContext<ProductContextValue | null>(null);

export function ProductProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useProducts();
  const [savedOverride, setSavedOverride] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null,
  );

  const products = useMemo(() => data?.items ?? [], [data]);

  // Derived active product: the saved choice when still valid, else the first.
  const productId = useMemo(() => {
    if (savedOverride && products.some((p) => p.id === savedOverride)) {
      return savedOverride;
    }
    return products[0]?.id ?? null;
  }, [savedOverride, products]);

  const setProductId = useCallback((id: string) => {
    setSavedOverride(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const createProductMutation = useCreateProduct();

  const createProduct = useCallback(
    async (name: string, description?: string) => {
      const created = await createProductMutation.mutateAsync({
        name,
        description,
      });
      setProductId(created.id);
      void qc.invalidateQueries({ queryKey: ["products"] });
      return created;
    },
    [createProductMutation, qc, setProductId],
  );

  const product = products.find((p) => p.id === productId) ?? null;

  return (
    <ProductContext.Provider
      value={{
        products,
        product,
        productId,
        setProductId,
        createProduct,
        loading: isLoading,
      }}
    >
      {children}
    </ProductContext.Provider>
  );
}

export function useProduct(): ProductContextValue {
  const ctx = useContext(ProductContext);
  if (!ctx) throw new Error("useProduct must be used inside ProductProvider");
  return ctx;
}

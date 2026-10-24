"use client";
import { useCallback, useSyncExternalStore } from "react";
import { restoreSession } from "@/lib/investigation";

const listeners = new Set<() => void>();
const memory = new Map<string, string>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** Tab-local persistence, scoped to a product; SSR never reads browser storage. */
export function useInvestigationSession<T>(name: string, productId: string | null, fallback: T) {
  const key = `happynest.investigation.${productId ?? "none"}.${name}`;
  const read = useCallback(() => {
    try { return sessionStorage.getItem(key) ?? memory.get(key) ?? null; }
    catch { return memory.get(key) ?? null; }
  }, [key]);
  const raw = useSyncExternalStore(subscribe, read, () => null);
  const value = restoreSession(raw, productId, fallback);
  const setValue = useCallback((next: T | ((old: T) => T)) => {
    if (!productId) return;
    const old = restoreSession(read(), productId, fallback);
    const value = typeof next === "function" ? (next as (old: T) => T)(old) : next;
    const serialized = JSON.stringify({ productId, value });
    memory.set(key, serialized);
    try { sessionStorage.setItem(key, serialized); } catch { /* session memory still works */ }
    for (const listener of listeners) listener();
  }, [key, productId, fallback, read]);
  return [value, setValue] as const;
}

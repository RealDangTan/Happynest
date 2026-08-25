"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export type User = { id: string; email: string; role: "pm" | "operations" };

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/api/auth/me"),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

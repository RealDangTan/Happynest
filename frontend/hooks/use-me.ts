"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export type User = { id: string; email: string; username?: string | null };

const meQueryKey = ["me"] as const;

export function getDisplayUsername(user?: User) {
  return user?.username || user?.email.split("@")[0] || "";
}

export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: ({ signal }) => apiFetch<User>("/api/auth/me", { signal }),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useUpdateUsername() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (username: string | null) =>
      apiFetch<User>("/api/auth/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      }),
    onSuccess: async (user) => {
      await queryClient.cancelQueries({ queryKey: meQueryKey });
      queryClient.setQueryData<User>(meQueryKey, (current) =>
        current?.id === user.id ? user : current,
      );
    },
  });
}

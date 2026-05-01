import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ServiceAction, ServiceItem } from "@/types";

export function useServices(filter?: "active" | "inactive" | "all") {
  return useQuery({
    queryKey: ["services", filter ?? "all"],
    queryFn: () =>
      api
        .get<ServiceItem[]>("/services", {
          params: filter && filter !== "all" ? { filter } : undefined,
        })
        .then((r) => r.data),
    refetchInterval: 10_000,
  });
}

export function useServiceDetail(name: string | null) {
  return useQuery({
    queryKey: ["services", "detail", name],
    queryFn: () =>
      api
        .get<Record<string, unknown>>(`/services/${encodeURIComponent(name as string)}`)
        .then((r) => r.data),
    enabled: !!name,
  });
}

export type ServiceActionResponse = { ok: boolean; output: string };

export function useServiceAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, action }: { name: string; action: ServiceAction }) =>
      api
        .post<ServiceActionResponse>(`/services/${encodeURIComponent(name)}/action`, {
          action,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["services"] });
    },
  });
}

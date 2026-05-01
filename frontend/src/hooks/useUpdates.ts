import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { UpdatesList, UpgradeResult } from "@/types";

const QK = ["updates"] as const;

export function useUpdatesList() {
  return useQuery({
    queryKey: QK,
    queryFn: () => api.get<UpdatesList>("/updates").then((r) => r.data),
    refetchInterval: 5 * 60_000,
  });
}

export function useApplySecurityUpdates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<UpgradeResult>("/updates/apply-security", undefined, { timeout: 15 * 60_000 }).then(
        (r) => r.data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useApplyAllUpdates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<UpgradeResult>("/updates/apply-all", undefined, { timeout: 30 * 60_000 }).then(
        (r) => r.data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

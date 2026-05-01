import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Alert } from "@/types";

export function useAlerts(status: "open" | "all" = "open") {
  return useQuery({
    queryKey: ["alerts", status],
    queryFn: () =>
      api
        .get<Alert[]>("/alerts", { params: { status } })
        .then((r) => r.data),
    refetchInterval: 5_000,
  });
}

export function useAckAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api
        .post<{ ok: boolean }>(`/alerts/${id}/ack`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { MetricsSnapshot } from "@/types";

export function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.get<MetricsSnapshot>("/metrics").then((r) => r.data),
    refetchInterval: 5_000,
  });
}

export function useMetricsHistory(limit = 60) {
  return useQuery({
    queryKey: ["metrics", "history", limit],
    queryFn: () =>
      api
        .get<MetricsSnapshot[]>("/metrics/history", { params: { limit } })
        .then((r) => r.data),
    refetchInterval: 10_000,
  });
}

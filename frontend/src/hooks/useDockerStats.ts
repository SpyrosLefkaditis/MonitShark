import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { DockerStats } from "@/types";

export function useDockerStats(id: string | null) {
  return useQuery({
    queryKey: ["docker", "stats", id],
    queryFn: () =>
      api
        .get<DockerStats>(
          `/docker/containers/${encodeURIComponent(id as string)}/stats`,
        )
        .then((r) => r.data),
    enabled: !!id,
    refetchInterval: 3_000,
  });
}

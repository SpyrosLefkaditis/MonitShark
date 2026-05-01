import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  DockerAction,
  DockerActionResult,
  DockerContainer,
  DockerContainerDetail,
} from "@/types";

export function useDockerContainers(showAll: boolean) {
  return useQuery({
    queryKey: ["docker", "containers", showAll],
    queryFn: () =>
      api
        .get<DockerContainer[]>("/docker/containers", {
          params: { all: showAll },
        })
        .then((r) => r.data),
    refetchInterval: 5_000,
  });
}

export function useDockerContainer(id: string | null) {
  return useQuery({
    queryKey: ["docker", "container", id],
    queryFn: () =>
      api
        .get<DockerContainerDetail>(
          `/docker/containers/${encodeURIComponent(id as string)}`,
        )
        .then((r) => r.data),
    enabled: !!id,
    refetchInterval: 5_000,
  });
}

export function useDockerAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: DockerAction }) =>
      api
        .post<DockerActionResult>(
          `/docker/containers/${encodeURIComponent(id)}/action`,
          { action },
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["docker", "containers"] });
      qc.invalidateQueries({ queryKey: ["docker", "container", vars.id] });
      qc.invalidateQueries({ queryKey: ["docker", "stats", vars.id] });
    },
  });
}

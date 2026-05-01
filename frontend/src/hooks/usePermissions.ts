import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FsEntry, FsInfo, FsListing } from "@/types";

export function useFsList(path: string | null) {
  return useQuery({
    queryKey: ["fs", "list", path],
    queryFn: () =>
      api.get<FsListing>("/fs/list", { params: { path } }).then((r) => r.data),
    enabled: !!path,
  });
}

export function useFsInfo(path: string | null) {
  return useQuery({
    queryKey: ["fs", "info", path],
    queryFn: () =>
      api.get<FsInfo>("/fs/info", { params: { path } }).then((r) => r.data),
    enabled: !!path,
  });
}

export type ChmodInput = { path: string; mode_octal: string };

export function useChmod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ChmodInput) =>
      api.post<FsEntry>("/fs/chmod", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fs"] });
    },
  });
}

export type ChownInput = {
  path: string;
  owner?: string | null;
  group?: string | null;
};

export function useChown() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ChownInput) =>
      api
        .post<FsEntry>("/fs/chown", {
          path: body.path,
          owner: body.owner ?? null,
          group: body.group ?? null,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fs"] });
    },
  });
}

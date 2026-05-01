import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { LogSearchResult, LogSources, LogTail } from "@/types";

export function useLogSources() {
  return useQuery({
    queryKey: ["logs", "sources"],
    queryFn: () => api.get<LogSources>("/logs/sources").then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useLogTail(path: string | null, lines = 200) {
  return useQuery({
    queryKey: ["logs", "tail", path, lines],
    queryFn: () =>
      api
        .get<LogTail>("/logs", { params: { path, lines } })
        .then((r) => r.data),
    enabled: !!path,
    refetchInterval: 3_000,
  });
}

export type LogSearchInput = {
  path: string;
  query: string;
  regex?: boolean;
  max_matches?: number;
};

export function useLogSearch() {
  return useMutation({
    mutationFn: (body: LogSearchInput) =>
      api
        .post<LogSearchResult>("/logs/search", {
          path: body.path,
          query: body.query,
          regex: body.regex ?? false,
          max_matches: body.max_matches ?? 200,
        })
        .then((r) => r.data),
  });
}

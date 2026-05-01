import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { CronEntry } from "@/types";

export function useCronJobs(user?: string) {
  return useQuery({
    queryKey: ["cron", user ?? "all"],
    queryFn: () =>
      api
        .get<CronEntry[]>("/cron", { params: user ? { user } : undefined })
        .then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export type CronCreateInput = {
  user: string;
  schedule: string;
  command: string;
  comment?: string | null;
};

export type CronUpdateInput = {
  schedule?: string;
  command?: string;
  comment?: string | null;
  enabled?: boolean;
};

export function useCronCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CronCreateInput) =>
      api.post<CronEntry>("/cron", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron"] });
    },
  });
}

export function useCronUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CronUpdateInput }) =>
      api.put<CronEntry>(`/cron/${encodeURIComponent(id)}`, body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron"] });
    },
  });
}

export function useCronDelete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<{ ok: boolean }>(`/cron/${encodeURIComponent(id)}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron"] });
    },
  });
}

export type CronRunInput = {
  command: string;
  args?: string[];
  timeout_s?: number;
};

export type CronRunResult = { rc: number; stdout: string; stderr: string };

export function useCronRun() {
  return useMutation({
    mutationFn: (body: CronRunInput) =>
      api
        .post<CronRunResult>("/cron/run", {
          command: body.command,
          args: body.args ?? [],
          timeout_s: body.timeout_s ?? 30,
        })
        .then((r) => r.data),
  });
}

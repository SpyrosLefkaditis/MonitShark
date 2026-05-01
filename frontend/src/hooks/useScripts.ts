import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  ScriptContent,
  ScriptFile,
  ScriptInstallServiceResult,
  ScriptRunResult,
  ScriptScheduleResult,
} from "@/types";

export function useScripts() {
  return useQuery({
    queryKey: ["scripts"],
    queryFn: () => api.get<ScriptFile[]>("/scripts").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useScript(name: string | null) {
  return useQuery({
    queryKey: ["scripts", name],
    queryFn: () =>
      api
        .get<ScriptContent>(`/scripts/${encodeURIComponent(name ?? "")}`)
        .then((r) => r.data),
    enabled: !!name,
  });
}

export type ScriptSaveInput = {
  name: string;
  content: string;
  make_executable?: boolean;
};

export function useSaveScript() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, content, make_executable }: ScriptSaveInput) =>
      api
        .put<ScriptFile>(`/scripts/${encodeURIComponent(name)}`, {
          content,
          make_executable: make_executable ?? true,
        })
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["scripts"] });
      qc.invalidateQueries({ queryKey: ["scripts", vars.name] });
    },
  });
}

export function useDeleteScript() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api
        .delete<{ name: string; deleted: boolean }>(`/scripts/${encodeURIComponent(name)}`)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scripts"] }),
  });
}

export type ScriptRunInput = {
  name: string;
  args?: string[];
  timeout_s?: number;
};

export function useRunScript() {
  return useMutation({
    mutationFn: ({ name, args, timeout_s }: ScriptRunInput) =>
      api
        .post<ScriptRunResult>(`/scripts/${encodeURIComponent(name)}/run`, {
          args: args ?? [],
          timeout_s: timeout_s ?? 60,
        })
        .then((r) => r.data),
  });
}

export type ScriptInstallServiceInput = {
  name: string;
  service_name: string;
  description?: string;
  restart?: "no" | "always" | "on-failure" | "on-abnormal";
};

export function useInstallScriptService() {
  return useMutation({
    mutationFn: ({ name, service_name, description, restart }: ScriptInstallServiceInput) =>
      api
        .post<ScriptInstallServiceResult>(
          `/scripts/${encodeURIComponent(name)}/install-service`,
          {
            service_name,
            description: description ?? "",
            restart: restart ?? "no",
          },
        )
        .then((r) => r.data),
  });
}

export type ScriptScheduleInput = {
  name: string;
  schedule: string;
  user?: string;
};

export function useScheduleScript() {
  return useMutation({
    mutationFn: ({ name, schedule, user }: ScriptScheduleInput) =>
      api
        .post<ScriptScheduleResult>(`/scripts/${encodeURIComponent(name)}/schedule`, {
          schedule,
          user: user ?? "root",
        })
        .then((r) => r.data),
  });
}

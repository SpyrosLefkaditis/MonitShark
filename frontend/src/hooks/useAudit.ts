import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { AuditAggregate, AuditReport, Finding, FindingStatus } from "@/types";

export function useAuditResults() {
  return useQuery({
    queryKey: ["audit", "last"],
    queryFn: async () => null as AuditAggregate | null,
    enabled: false,
    staleTime: Infinity,
  });
}

export function useRunAllAudits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<AuditAggregate>("/audits/run-all").then((r) => r.data),
    onSuccess: (data) => {
      qc.setQueryData(["audit", "last"], data);
      qc.invalidateQueries({ queryKey: ["findings"] });
    },
  });
}

export function useRunAudit(name: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<AuditReport>(`/audits/${encodeURIComponent(name)}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings"] });
    },
  });
}

export function useFindings(status?: FindingStatus) {
  return useQuery({
    queryKey: ["findings", status ?? "all"],
    queryFn: () =>
      api
        .get<Finding[]>("/findings", { params: status ? { status } : undefined })
        .then((r) => r.data),
  });
}

export function useDismissFinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api
        .post<{ ok: boolean }>(`/findings/${encodeURIComponent(id)}/dismiss`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings"] });
      qc.invalidateQueries({ queryKey: ["audit", "last"] });
    },
  });
}

export type ApplyFixResponse = { ok: boolean; message: string };

export function useApplyFix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api
        .post<ApplyFixResponse>(`/findings/${encodeURIComponent(id)}/apply-fix`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings"] });
    },
  });
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  FirewallActionResult,
  FirewallRule,
  FirewallRuleInput,
  FirewallStatus,
} from "@/types";

const QK = ["firewall"] as const;

export function useFirewallStatus() {
  return useQuery({
    queryKey: [...QK, "status"],
    queryFn: () => api.get<FirewallStatus>("/firewall/status").then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useFirewallRules() {
  return useQuery({
    queryKey: [...QK, "rules"],
    queryFn: () => api.get<FirewallRule[]>("/firewall/rules").then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useFirewallAddRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FirewallRuleInput) =>
      api.post<FirewallActionResult>("/firewall/rules", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useFirewallDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleNumber: number) =>
      api.delete<FirewallActionResult>(`/firewall/rules/${ruleNumber}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useFirewallEnable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<FirewallActionResult>("/firewall/enable").then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useFirewallDisable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<FirewallActionResult>("/firewall/disable").then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK });
    },
  });
}

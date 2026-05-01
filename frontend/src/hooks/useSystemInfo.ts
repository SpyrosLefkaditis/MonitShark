import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CpuCore,
  DiskIO,
  HostInfo,
  KernelModule,
  ListeningPort,
  NetIface,
  Sensor,
} from "@/types";

const REFRESH_MS = 5_000;

export function useSystemInfo() {
  return useQuery({
    queryKey: ["system", "info"],
    queryFn: () => api.get<HostInfo>("/system/info").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useCpuPerCore() {
  return useQuery({
    queryKey: ["system", "cpu-per-core"],
    queryFn: () =>
      api
        .get<CpuCore[]>("/system/cpu-per-core", { params: { interval: 0.2 } })
        .then((r) => r.data),
    refetchInterval: REFRESH_MS,
  });
}

export function useDiskIO() {
  return useQuery({
    queryKey: ["system", "disk-io"],
    queryFn: () => api.get<DiskIO[]>("/system/disk-io").then((r) => r.data),
    refetchInterval: REFRESH_MS,
  });
}

export function useNetPerIface(includeVirtual: boolean) {
  return useQuery({
    queryKey: ["system", "net-per-iface", includeVirtual],
    queryFn: () =>
      api
        .get<NetIface[]>("/system/net-per-iface", {
          params: { include_virtual: includeVirtual },
        })
        .then((r) => r.data),
    refetchInterval: REFRESH_MS,
  });
}

export function useSensors() {
  return useQuery({
    queryKey: ["system", "sensors"],
    queryFn: () => api.get<Sensor[]>("/system/sensors").then((r) => r.data),
    refetchInterval: REFRESH_MS,
  });
}

export function useKernelModules() {
  return useQuery({
    queryKey: ["system", "kernel-modules"],
    queryFn: () =>
      api.get<KernelModule[]>("/system/kernel-modules").then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useListeningPorts() {
  return useQuery({
    queryKey: ["system", "listening"],
    queryFn: () =>
      api.get<ListeningPort[]>("/system/listening").then((r) => r.data),
    refetchInterval: 10_000,
  });
}

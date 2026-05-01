import { Activity, Cpu, HardDrive, MemoryStick, Network } from "lucide-react";

import { AlertsList } from "@/components/dashboard/AlertsList";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { MetricChart } from "@/components/dashboard/MetricChart";
import { ProcessTable } from "@/components/dashboard/ProcessTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLiveMetrics } from "@/hooks/useLiveMetrics";
import { formatBytes, formatPercent } from "@/lib/format";
import type { MetricsSnapshot } from "@/types";

function rootDisk(snap: MetricsSnapshot) {
  return snap.disks.find((d) => d.mountpoint === "/") ?? snap.disks[0];
}

function netSeries(buffer: MetricsSnapshot[]): { rxRate: number[]; bytes: number } {
  // Compute byte/sec deltas vs previous frame.
  const rates: number[] = [];
  for (let i = 1; i < buffer.length; i++) {
    const prev = buffer[i - 1];
    const cur = buffer[i];
    const dt = Math.max(1, cur.ts - prev.ts);
    const dRx = Math.max(0, cur.net.bytes_recv - prev.net.bytes_recv);
    const dTx = Math.max(0, cur.net.bytes_sent - prev.net.bytes_sent);
    rates.push((dRx + dTx) / dt);
  }
  const bytes = rates.length ? rates[rates.length - 1] : 0;
  return { rxRate: rates, bytes };
}

export function DashboardPage() {
  const { buffer, latest, readyState, isLoading } = useLiveMetrics();

  if (isLoading || !latest) {
    return (
      <div className="grid gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const cpuSeries = buffer.map((s) => s.cpu.percent);
  const memSeries = buffer.map((s) => s.memory.percent);
  const root = rootDisk(latest);
  const diskSeries = buffer.map((s) => {
    const r = rootDisk(s);
    return r ? r.percent : 0;
  });
  const { rxRate, bytes } = netSeries(buffer);

  const wsBadge =
    readyState === WebSocket.OPEN ? (
      <span className="text-[11px] text-emerald-500 font-mono">● live</span>
    ) : (
      <span className="text-[11px] text-amber-500 font-mono">○ polling</span>
    );

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          title="CPU"
          value={formatPercent(latest.cpu.percent)}
          subtitle={`load ${latest.cpu.load_1.toFixed(2)}, ${latest.cpu.count} cores`}
          series={cpuSeries}
          icon={Cpu}
          lowerIsBetter
          domain={[0, 100]}
        />
        <MetricCard
          title="Memory"
          value={formatPercent(latest.memory.percent)}
          subtitle={`${formatBytes(latest.memory.used)} / ${formatBytes(latest.memory.total)}`}
          series={memSeries}
          icon={MemoryStick}
          color="#22c55e"
          lowerIsBetter
          domain={[0, 100]}
        />
        <MetricCard
          title="Disk /"
          value={root ? formatPercent(root.percent) : "—"}
          subtitle={
            root ? `${formatBytes(root.used)} / ${formatBytes(root.total)}` : "no mountpoint"
          }
          series={diskSeries}
          icon={HardDrive}
          color="#f59e0b"
          lowerIsBetter
          domain={[0, 100]}
        />
        <MetricCard
          title="Network"
          value={`${formatBytes(bytes)}/s`}
          subtitle={`${formatBytes(latest.net.bytes_recv)} ↓ / ${formatBytes(latest.net.bytes_sent)} ↑`}
          series={rxRate}
          icon={Network}
          color="#a78bfa"
        />
      </div>

      <Card>
        <CardHeader className="pb-3 flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="size-4" /> Last 60 frames
          </CardTitle>
          {wsBadge}
        </CardHeader>
        <CardContent className="pt-0">
          <MetricChart buffer={buffer} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Top processes</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ProcessTable processes={latest.top_processes} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Open alerts</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <AlertsList />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import {
  Cpu,
  HardDrive,
  Network as NetworkIcon,
  Plug,
  Server,
  Thermometer,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useCpuPerCore,
  useDiskIO,
  useListeningPorts,
  useNetPerIface,
  useSensors,
  useSystemInfo,
} from "@/hooks/useSystemInfo";
import { cn } from "@/lib/utils";
import { formatBytes, formatDuration } from "@/lib/format";
import type { Sensor } from "@/types";

function tempColor(s: Sensor): string {
  if (s.kind !== "temperature") return "text-foreground";
  const high = s.high ?? 80;
  const crit = s.critical ?? 100;
  if (s.current >= crit) return "text-destructive";
  if (s.current >= high) return "text-amber-500";
  if (s.current >= 60) return "text-amber-500";
  if (s.current < 60) return "text-emerald-500";
  return "text-foreground";
}

export function SystemPage() {
  const info = useSystemInfo();
  const cpu = useCpuPerCore();
  const disk = useDiskIO();
  const [includeVirtual, setIncludeVirtual] = useState(false);
  const net = useNetPerIface(includeVirtual);
  const sensorsQ = useSensors();
  const ports = useListeningPorts();

  const cpuList = cpu.data ?? [];
  const sortedNet = useMemo(() => {
    return (net.data ?? []).slice(0, 6);
  }, [net.data]);

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="size-4" /> Host
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5 text-sm">
            {info.isLoading ? (
              <Skeleton className="h-24" />
            ) : info.data ? (
              <ul className="space-y-1 font-mono text-xs">
                <li>
                  <span className="text-muted-foreground">hostname:</span> {info.data.hostname}
                </li>
                <li>
                  <span className="text-muted-foreground">distro:</span>{" "}
                  {info.data.distro || "—"}
                </li>
                <li>
                  <span className="text-muted-foreground">kernel:</span> {info.data.kernel}
                </li>
                <li>
                  <span className="text-muted-foreground">arch:</span> {info.data.arch}
                </li>
                <li>
                  <span className="text-muted-foreground">cpu:</span>{" "}
                  {info.data.cpu_model || "—"}
                </li>
                <li>
                  <span className="text-muted-foreground">cores:</span>{" "}
                  {info.data.cpu_cores_physical} physical /{" "}
                  {info.data.cpu_cores_logical} logical
                </li>
                <li>
                  <span className="text-muted-foreground">ram:</span>{" "}
                  {formatBytes(info.data.total_ram_bytes)}
                </li>
                <li>
                  <span className="text-muted-foreground">uptime:</span>{" "}
                  {formatDuration(info.data.uptime_seconds)}
                </li>
              </ul>
            ) : (
              <div className="text-xs text-destructive">Failed to load host info.</div>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="size-4" /> CPU per core
              <span className="ml-2 text-xs text-muted-foreground font-normal font-mono">
                {cpuList.length} cores
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {cpu.isLoading ? (
              <Skeleton className="h-32" />
            ) : cpuList.length === 0 ? (
              <div className="text-xs text-muted-foreground">No data.</div>
            ) : (
              <ul className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {cpuList.map((c) => (
                  <li
                    key={c.core}
                    className="space-y-1 text-xs font-mono"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">core {c.core}</span>
                      <span className="tabular-nums">
                        {c.percent.toFixed(0)}%
                        {c.freq_mhz != null && (
                          <span className="text-muted-foreground ml-1.5">
                            {Math.round(c.freq_mhz)}MHz
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          c.percent < 50
                            ? "bg-emerald-500"
                            : c.percent < 80
                            ? "bg-amber-500"
                            : "bg-destructive",
                        )}
                        style={{ width: `${Math.min(100, Math.max(0, c.percent))}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="size-4" /> Disk I/O
            </CardTitle>
          </CardHeader>
          <CardContent>
            {disk.isLoading ? (
              <Skeleton className="h-24" />
            ) : (disk.data ?? []).length === 0 ? (
              <div className="text-xs text-muted-foreground">
                Two samples needed; refresh in a few seconds.
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead className="text-muted-foreground border-b border-border">
                  <tr>
                    <th className="text-left py-1.5">Disk</th>
                    <th className="text-right py-1.5">Read MB/s</th>
                    <th className="text-right py-1.5">Write MB/s</th>
                    <th className="text-right py-1.5">Busy%</th>
                  </tr>
                </thead>
                <tbody>
                  {(disk.data ?? []).map((d) => (
                    <tr key={d.name} className="border-b border-border/40">
                      <td className="py-1.5">{d.name}</td>
                      <td className="text-right tabular-nums">{d.read_mb_s.toFixed(2)}</td>
                      <td className="text-right tabular-nums">{d.write_mb_s.toFixed(2)}</td>
                      <td className="text-right tabular-nums">
                        {d.busy_percent != null ? `${d.busy_percent.toFixed(0)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <NetworkIcon className="size-4" /> Network per interface
            </CardTitle>
            <div className="flex items-center gap-2">
              <Switch
                id="net-include-virtual"
                checked={includeVirtual}
                onCheckedChange={setIncludeVirtual}
              />
              <Label htmlFor="net-include-virtual" className="text-xs cursor-pointer">
                Include virtual
              </Label>
            </div>
          </CardHeader>
          <CardContent>
            {net.isLoading ? (
              <Skeleton className="h-24" />
            ) : sortedNet.length === 0 ? (
              <div className="text-xs text-muted-foreground">
                Two samples needed; refresh in a few seconds.
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead className="text-muted-foreground border-b border-border">
                  <tr>
                    <th className="text-left py-1.5">Interface</th>
                    <th className="text-right py-1.5">↓ /s</th>
                    <th className="text-right py-1.5">↑ /s</th>
                    <th className="text-right py-1.5">errors</th>
                    <th className="text-right py-1.5">drops</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedNet.map((n) => (
                    <tr key={n.name} className="border-b border-border/40">
                      <td className="py-1.5">
                        {n.name}
                        {n.is_virtual && (
                          <Badge variant="outline" className="ml-2 text-[9px] py-0">
                            virt
                          </Badge>
                        )}
                      </td>
                      <td className="text-right tabular-nums">
                        {formatBytes(n.bytes_recv_per_sec)}
                      </td>
                      <td className="text-right tabular-nums">
                        {formatBytes(n.bytes_sent_per_sec)}
                      </td>
                      <td className="text-right tabular-nums">
                        {n.errors_in + n.errors_out}
                      </td>
                      <td className="text-right tabular-nums">
                        {n.drops_in + n.drops_out}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Thermometer className="size-4" /> Sensors
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sensorsQ.isLoading ? (
              <Skeleton className="h-24" />
            ) : (sensorsQ.data ?? []).length === 0 ? (
              <div className="text-xs text-muted-foreground">No sensors available.</div>
            ) : (
              <ul className="space-y-1 text-xs font-mono">
                {(sensorsQ.data ?? []).map((s, i) => (
                  <li
                    key={`${s.chip}-${s.label}-${i}`}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="truncate">
                      <span className="text-muted-foreground">{s.chip}</span> {s.label}
                    </span>
                    <span className={cn("tabular-nums", tempColor(s))}>
                      {s.current.toFixed(1)} {s.unit}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plug className="size-4" /> Listening ports
              <span className="ml-2 text-xs text-muted-foreground font-normal font-mono">
                {(ports.data ?? []).length} total
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {ports.isLoading ? (
              <Skeleton className="h-24" />
            ) : (ports.data ?? []).length === 0 ? (
              <div className="text-xs text-muted-foreground">No listening sockets visible.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead className="text-muted-foreground border-b border-border">
                    <tr>
                      <th className="text-left py-1.5">Address</th>
                      <th className="text-left py-1.5">Proto</th>
                      <th className="text-right py-1.5">PID</th>
                      <th className="text-left py-1.5 pl-3">Process</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(ports.data ?? []).map((p, i) => (
                      <tr key={`${p.laddr}-${p.proto}-${i}`} className="border-b border-border/40">
                        <td className="py-1.5">{p.laddr}</td>
                        <td className="py-1.5">{p.proto}</td>
                        <td className="py-1.5 text-right tabular-nums">
                          {p.pid ?? "—"}
                        </td>
                        <td className="py-1.5 pl-3">{p.process || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

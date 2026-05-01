import { isAxiosError } from "axios";
import {
  Activity,
  Container as ContainerIcon,
  Eraser,
  Heart,
  Pause,
  Play,
  Power,
  RefreshCw,
  RotateCw,
  ScrollText,
  Square,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useDockerAction,
  useDockerContainer,
  useDockerContainers,
} from "@/hooks/useDocker";
import { useDockerLogs } from "@/hooks/useDockerLogs";
import { useDockerStats } from "@/hooks/useDockerStats";
import { cn } from "@/lib/utils";
import { formatBytes, formatPercent } from "@/lib/format";
import type {
  DockerAction,
  DockerContainer,
  DockerContainerDetail,
} from "@/types";

type ActionEntry = { action: DockerAction; label: string; Icon: typeof Play; tone?: "destructive" };

const ALL_ACTIONS: ActionEntry[] = [
  { action: "start", label: "Start", Icon: Play },
  { action: "stop", label: "Stop", Icon: Square, tone: "destructive" },
  { action: "restart", label: "Restart", Icon: RotateCw },
  { action: "pause", label: "Pause", Icon: Pause },
  { action: "unpause", label: "Unpause", Icon: Play },
  { action: "kill", label: "Kill", Icon: Zap, tone: "destructive" },
];

function actionsForState(state: string): ActionEntry[] {
  const s = (state || "").toLowerCase();
  if (s === "running") {
    return ALL_ACTIONS.filter((a) =>
      ["stop", "restart", "pause", "kill"].includes(a.action),
    );
  }
  if (s === "paused") {
    return ALL_ACTIONS.filter((a) => ["unpause", "stop", "kill"].includes(a.action));
  }
  if (s === "exited" || s === "dead" || s === "created") {
    return ALL_ACTIONS.filter((a) => a.action === "start");
  }
  if (s === "restarting") {
    return ALL_ACTIONS.filter((a) => ["stop", "kill"].includes(a.action));
  }
  return ALL_ACTIONS.filter((a) => a.action === "start");
}

function statusVariant(state: string): "default" | "success" | "warning" | "destructive" | "outline" {
  const s = (state || "").toLowerCase();
  if (s === "running") return "success";
  if (s === "paused") return "warning";
  if (s === "exited" || s === "dead") return "destructive";
  return "outline";
}

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

function formatPort(p: { container_port: string; proto: string; host_ip: string | null; host_port: string | null }): string {
  if (p.host_port) {
    const ip = p.host_ip && p.host_ip !== "0.0.0.0" ? `${p.host_ip}:` : "";
    return `${ip}${p.host_port} → ${p.container_port}/${p.proto}`;
  }
  return `${p.container_port}/${p.proto}`;
}

export function DockerPage() {
  const [showAll, setShowAll] = useState(true);
  const containers = useDockerContainers(showAll);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [logsId, setLogsId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{
    container: DockerContainer | DockerContainerDetail;
    action: DockerAction;
  } | null>(null);

  const detail = useDockerContainer(selectedId);
  const stats = useDockerStats(selectedId);
  const action = useDockerAction();

  const list = containers.data ?? [];

  const onConfirm = async () => {
    if (!pendingAction) return;
    const { container, action: act } = pendingAction;
    try {
      const r = await action.mutateAsync({ id: container.id, action: act });
      toast.success(`${act} ${container.name}`, {
        description: `state: ${r.state}`,
      });
    } catch (e) {
      toast.error(`Failed to ${act} ${container.name}`, {
        description: describeError(e),
      });
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <ContainerIcon className="size-4" /> Containers
            <span className="ml-2 text-xs text-muted-foreground font-normal font-mono">
              {list.length} total
            </span>
          </CardTitle>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Switch
                id="docker-show-stopped"
                checked={showAll}
                onCheckedChange={setShowAll}
              />
              <Label htmlFor="docker-show-stopped" className="text-xs cursor-pointer">
                Show stopped
              </Label>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => containers.refetch()}
              disabled={containers.isFetching}
              className="gap-1.5"
            >
              <RefreshCw
                className={containers.isFetching ? "size-3.5 animate-spin" : "size-3.5"}
              />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {containers.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : containers.error ? (
            <div className="py-10 text-center text-sm text-destructive">
              Failed to load containers. {(containers.error as Error).message}
            </div>
          ) : list.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              No containers {showAll ? "found" : "running"}.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-muted-foreground border-b border-border">
                  <tr>
                    <th className="text-left py-2 px-2 font-medium">Name</th>
                    <th className="text-left py-2 px-2 font-medium">Image</th>
                    <th className="text-left py-2 px-2 font-medium">Status</th>
                    <th className="text-left py-2 px-2 font-medium">Ports</th>
                    <th className="text-left py-2 px-2 font-medium">Health</th>
                    <th className="text-right py-2 px-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((c) => (
                    <tr
                      key={c.id}
                      className={cn(
                        "border-b border-border/50 hover:bg-accent/40 transition-colors cursor-pointer",
                        selectedId === c.id && "bg-accent/60",
                      )}
                      onClick={() => setSelectedId(c.id)}
                    >
                      <td className="py-2 px-2 font-medium">
                        <div className="font-mono">{c.name}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          {c.short_id}
                        </div>
                      </td>
                      <td className="py-2 px-2 text-xs font-mono text-muted-foreground truncate max-w-[280px]">
                        {c.image}
                      </td>
                      <td className="py-2 px-2">
                        <Badge variant={statusVariant(c.state)}>{c.state}</Badge>
                      </td>
                      <td className="py-2 px-2 text-xs font-mono text-muted-foreground">
                        {c.ports.length === 0
                          ? "—"
                          : c.ports
                              .slice(0, 3)
                              .map((p) => formatPort(p))
                              .join(", ") +
                            (c.ports.length > 3 ? ` +${c.ports.length - 3}` : "")}
                      </td>
                      <td className="py-2 px-2">
                        {c.health ? (
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 text-xs",
                              c.health === "healthy" && "text-emerald-500",
                              c.health === "unhealthy" && "text-destructive",
                              c.health === "starting" && "text-amber-500",
                            )}
                          >
                            <Heart className="size-3" /> {c.health}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="py-2 px-2">
                        <div
                          className="flex items-center gap-1 justify-end"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1.5 h-7"
                            onClick={() => setLogsId(c.id)}
                          >
                            <ScrollText className="size-3" /> Logs
                          </Button>
                          {actionsForState(c.state).map(({ action: a, label, Icon, tone }) => (
                            <Button
                              key={a}
                              variant={tone === "destructive" ? "destructive" : "outline"}
                              size="sm"
                              className="gap-1 h-7 px-2"
                              onClick={() => setPendingAction({ container: c, action: a })}
                              title={label}
                            >
                              <Icon className="size-3" />
                            </Button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedId && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="size-4" />
              Container detail
              {detail.data && (
                <span className="ml-2 text-xs text-muted-foreground font-normal font-mono">
                  {detail.data.name}
                </span>
              )}
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedId(null)}
              className="text-xs"
            >
              Close
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {detail.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-6" />
                ))}
              </div>
            ) : detail.error ? (
              <div className="text-destructive">
                {(detail.error as Error).message}
              </div>
            ) : detail.data ? (
              <ContainerDetail
                detail={detail.data}
                stats={stats.data ?? null}
                onAction={(act) =>
                  setPendingAction({ container: detail.data!, action: act })
                }
              />
            ) : null}
          </CardContent>
        </Card>
      )}

      <ContainerActionDialog
        open={!!pendingAction}
        onOpenChange={(o) => !o && setPendingAction(null)}
        container={pendingAction?.container ?? null}
        action={pendingAction?.action ?? null}
        onConfirm={onConfirm}
        pending={action.isPending}
      />

      <LogsSheet
        containerId={logsId}
        containerName={
          list.find((c) => c.id === logsId)?.name ?? logsId ?? ""
        }
        onClose={() => setLogsId(null)}
      />
    </div>
  );
}

function ContainerDetail({
  detail,
  stats,
  onAction,
}: {
  detail: DockerContainerDetail;
  stats: import("@/types").DockerStats | null;
  onAction: (a: DockerAction) => void;
}) {
  const validActions = actionsForState(detail.state);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={statusVariant(detail.state)}>{detail.state}</Badge>
        {detail.health && (
          <Badge
            variant={
              detail.health === "healthy"
                ? "success"
                : detail.health === "unhealthy"
                ? "destructive"
                : "warning"
            }
          >
            health: {detail.health}
          </Badge>
        )}
        <span className="text-xs text-muted-foreground font-mono">{detail.id.slice(0, 12)}</span>
        <div className="ml-auto flex flex-wrap gap-1.5">
          {validActions.map(({ action: a, label, Icon, tone }) => (
            <Button
              key={a}
              variant={tone === "destructive" ? "destructive" : "outline"}
              size="sm"
              className="gap-1.5"
              onClick={() => onAction(a)}
            >
              <Icon className="size-3.5" />
              {label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DetailSection title="Image">
          <div className="font-mono text-xs break-all">{detail.image}</div>
          {detail.image_id && (
            <div className="text-[11px] text-muted-foreground font-mono break-all">
              {detail.image_id}
            </div>
          )}
        </DetailSection>

        <DetailSection title="Command">
          {detail.command.length > 0 || detail.entrypoint.length > 0 ? (
            <div className="font-mono text-xs">
              {[...detail.entrypoint, ...detail.command].join(" ") || "—"}
            </div>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </DetailSection>

        <DetailSection title="Network mode">
          <div className="font-mono text-xs">{detail.network_mode || "—"}</div>
          {Object.entries(detail.networks).length > 0 && (
            <ul className="mt-2 space-y-1">
              {Object.entries(detail.networks).map(([name, n]) => (
                <li key={name} className="text-xs font-mono text-muted-foreground">
                  {name}: {n.ip_address ?? "—"}
                </li>
              ))}
            </ul>
          )}
        </DetailSection>

        <DetailSection title="Restart policy">
          <div className="font-mono text-xs">
            {String(
              (detail.restart_policy as { Name?: string })?.Name ?? "—",
            )}
          </div>
        </DetailSection>

        <DetailSection title="Ports">
          {detail.ports.length === 0 ? (
            <span className="text-muted-foreground">—</span>
          ) : (
            <ul className="space-y-1">
              {detail.ports.map((p, i) => (
                <li key={i} className="text-xs font-mono text-muted-foreground">
                  {formatPort(p)}
                </li>
              ))}
            </ul>
          )}
        </DetailSection>

        <DetailSection title="Stats">
          {stats ? (
            <div className="space-y-1 text-xs font-mono">
              <div>cpu: {formatPercent(stats.cpu_percent)}</div>
              <div>
                mem: {formatBytes(stats.memory_usage)} /{" "}
                {formatBytes(stats.memory_limit)} (
                {formatPercent(stats.memory_percent)})
              </div>
              <div>
                net: {formatBytes(stats.net_rx)} ↓ /{" "}
                {formatBytes(stats.net_tx)} ↑
              </div>
              <div>
                io: {formatBytes(stats.block_read)} read /{" "}
                {formatBytes(stats.block_write)} write
              </div>
            </div>
          ) : (
            <span className="text-muted-foreground">loading…</span>
          )}
        </DetailSection>
      </div>

      {detail.mounts.length > 0 && (
        <DetailSection title="Mounts">
          <ul className="space-y-1">
            {detail.mounts.map((m, i) => (
              <li key={i} className="text-xs font-mono text-muted-foreground">
                {m.source} → {m.destination} ({m.mode || (m.rw ? "rw" : "ro")})
              </li>
            ))}
          </ul>
        </DetailSection>
      )}

      {Object.keys(detail.labels).length > 0 && (
        <DetailSection title="Labels">
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-1">
            {Object.entries(detail.labels).map(([k, v]) => (
              <li key={k} className="text-xs font-mono text-muted-foreground truncate">
                <span className="text-foreground/80">{k}</span>: {v}
              </li>
            ))}
          </ul>
        </DetailSection>
      )}

      {detail.env.length > 0 && (
        <DetailSection title="Environment">
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-1">
            {detail.env.map((e, i) => (
              <li key={`${e.key}-${i}`} className="text-xs font-mono text-muted-foreground truncate">
                <span className="text-foreground/80">{e.key}</span>={e.value}
              </li>
            ))}
          </ul>
        </DetailSection>
      )}
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">
        {title}
      </div>
      <div>{children}</div>
    </div>
  );
}

function ContainerActionDialog({
  open,
  onOpenChange,
  container,
  action,
  onConfirm,
  pending,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  container: DockerContainer | DockerContainerDetail | null;
  action: DockerAction | null;
  onConfirm: () => void;
  pending: boolean;
}) {
  const destructive = action === "stop" || action === "kill";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {action ? `Confirm ${action}` : "Confirm action"}
          </DialogTitle>
          <DialogDescription>
            {container && action
              ? `Run "${action}" on container "${container.name}" (${container.short_id})?`
              : null}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? "Running…" : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LogsSheet({
  containerId,
  containerName,
  onClose,
}: {
  containerId: string | null;
  containerName: string;
  onClose: () => void;
}) {
  const open = !!containerId;
  const { lines, paused, togglePause, clear, readyState, error } = useDockerLogs(
    containerId,
    { tail: 200, follow: true, enabled: open },
  );
  const scrollRef = useRef<HTMLPreElement>(null);

  // Autoscroll to bottom on new lines (unless user has paused).
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || paused) return;
    el.scrollTop = el.scrollHeight;
  }, [lines, paused]);

  const status = useMemo(() => {
    if (error) return { label: error, tone: "text-destructive" };
    if (readyState === WebSocket.OPEN) return { label: "live", tone: "text-emerald-500" };
    if (readyState === WebSocket.CONNECTING)
      return { label: "connecting", tone: "text-amber-500" };
    return { label: "disconnected", tone: "text-muted-foreground" };
  }, [readyState, error]);

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-3xl md:max-w-3xl flex flex-col"
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <ScrollText className="size-4" />
            Logs
            <span className="font-mono text-sm text-muted-foreground">{containerName}</span>
          </SheetTitle>
          <SheetDescription>
            Live tail of stdout/stderr. Most recent lines at the bottom.
          </SheetDescription>
        </SheetHeader>
        <div className="flex items-center gap-2 mt-3">
          <span className={cn("text-[11px] font-mono", status.tone)}>
            ● {status.label}
          </span>
          <span className="text-[11px] text-muted-foreground font-mono">
            {lines.length} lines
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={togglePause}
            >
              {paused ? <Play className="size-3.5" /> : <Pause className="size-3.5" />}
              {paused ? "Resume" : "Pause"}
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={clear}>
              <Eraser className="size-3.5" />
              Clear
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose} className="gap-1.5">
              <Power className="size-3.5" />
              Close
            </Button>
          </div>
        </div>
        <pre
          ref={scrollRef}
          className="mt-3 flex-1 overflow-auto rounded-md bg-muted/40 border border-border p-3 font-mono text-[11px] leading-snug whitespace-pre-wrap break-words"
        >
          {lines.length === 0 ? (
            <span className="text-muted-foreground">Waiting for log lines…</span>
          ) : (
            lines.map((l) => (
              <div key={l.id}>{l.line}</div>
            ))
          )}
        </pre>
      </SheetContent>
    </Sheet>
  );
}

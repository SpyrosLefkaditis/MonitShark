import { isAxiosError } from "axios";
import { ChevronDown, ChevronRight, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ApplyUpdatesDialog, type ApplyKind } from "@/components/updates/ApplyUpdatesDialog";
import { UpgradablePackagesTable } from "@/components/updates/UpgradablePackagesTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useApplyAllUpdates,
  useApplySecurityUpdates,
  useUpdatesList,
} from "@/hooks/useUpdates";
import { cn } from "@/lib/utils";
import type { UpgradeResult } from "@/types";

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

export function UpdatesPage() {
  const { data, isLoading, error, refetch, isFetching } = useUpdatesList();
  const applySecurity = useApplySecurityUpdates();
  const applyAll = useApplyAllUpdates();

  const [pendingKind, setPendingKind] = useState<ApplyKind | null>(null);
  const [lastResult, setLastResult] = useState<{ kind: ApplyKind; result: UpgradeResult } | null>(
    null,
  );
  const [outputOpen, setOutputOpen] = useState(true);

  const total = data?.total ?? 0;
  const securityCount = data?.security_count ?? 0;
  const otherCount = Math.max(0, total - securityCount);
  const pkgs = data?.packages ?? [];
  const pm = data?.package_manager ?? "unknown";

  const applyPending = applySecurity.isPending || applyAll.isPending;

  const onConfirm = async () => {
    if (!pendingKind) return;
    const kind = pendingKind;
    setPendingKind(null);
    try {
      const result =
        kind === "security"
          ? await applySecurity.mutateAsync()
          : await applyAll.mutateAsync();
      setLastResult({ kind, result });
      setOutputOpen(true);
      if (result.ok) {
        toast.success(`${kind === "security" ? "Security" : "All"} updates applied (rc=${result.rc}).`);
      } else {
        toast.error(`${kind === "security" ? "Security" : "All"} updates failed (rc=${result.rc}).`);
      }
    } catch (e) {
      toast.error("Update command failed.", { description: describeError(e) });
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">System updates</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Package manager:{" "}
              <span className="font-mono text-foreground">{pm}</span>
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={cn("size-4", isFetching && "animate-spin")} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-20" />
          ) : error ? (
            <div className="py-6 text-center text-sm text-destructive">
              Failed to load updates. {describeError(error)}
            </div>
          ) : pm === "unknown" ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Could not detect a supported package manager (apt or dnf) on this host.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat
                label="Total upgradable"
                value={total}
                tone="default"
              />
              <Stat
                label="Security"
                value={securityCount}
                tone={securityCount > 0 ? "danger" : "default"}
                icon={<ShieldAlert className="size-4" />}
              />
              <Stat label="Other" value={otherCount} tone="muted" />
            </div>
          )}
          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            <Button
              autoFocus
              onClick={() => setPendingKind("security")}
              disabled={applyPending || securityCount === 0 || pm === "unknown"}
            >
              Apply security updates
              {securityCount > 0 ? (
                <Badge variant="destructive" className="ml-2">
                  {securityCount}
                </Badge>
              ) : null}
            </Button>
            <Button
              variant="outline"
              onClick={() => setPendingKind("all")}
              disabled={applyPending || total === 0 || pm === "unknown"}
            >
              Apply all updates
              {total > 0 ? (
                <Badge variant="outline" className="ml-2">
                  {total}
                </Badge>
              ) : null}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upgradable packages</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : (
            <UpgradablePackagesTable packages={pkgs} />
          )}
        </CardContent>
      </Card>

      {lastResult && (
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                Last run output
                <Badge variant={lastResult.result.ok ? "success" : "destructive"}>
                  rc {lastResult.result.rc}
                </Badge>
                <Badge variant="outline">
                  {lastResult.kind === "security" ? "security" : "all"}
                </Badge>
              </CardTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOutputOpen((o) => !o)}
              className="gap-1.5"
            >
              {outputOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              {outputOpen ? "Collapse" : "Expand"}
            </Button>
          </CardHeader>
          {outputOpen && (
            <CardContent className="space-y-3">
              {lastResult.result.stdout && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">stdout</p>
                  <pre className="font-mono text-xs bg-muted/50 rounded p-3 overflow-x-auto whitespace-pre-wrap max-h-[24rem]">
                    {lastResult.result.stdout}
                  </pre>
                </div>
              )}
              {lastResult.result.stderr && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">stderr</p>
                  <pre className="font-mono text-xs bg-destructive/10 text-destructive-foreground rounded p-3 overflow-x-auto whitespace-pre-wrap max-h-[24rem]">
                    {lastResult.result.stderr}
                  </pre>
                </div>
              )}
              {!lastResult.result.stdout && !lastResult.result.stderr && (
                <p className="text-xs text-muted-foreground">No output captured.</p>
              )}
            </CardContent>
          )}
        </Card>
      )}

      <ApplyUpdatesDialog
        open={!!pendingKind}
        onOpenChange={(o) => !o && setPendingKind(null)}
        kind={pendingKind}
        onConfirm={onConfirm}
        pending={applyPending}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: "default" | "danger" | "muted";
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-md border border-border px-3 py-3 flex items-center justify-between",
        tone === "danger" && "border-destructive/40",
      )}
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      </div>
      <span
        className={cn(
          "text-2xl font-semibold tabular-nums",
          tone === "danger" && value > 0 && "text-destructive",
          tone === "muted" && "text-muted-foreground",
        )}
      >
        {value}
      </span>
    </div>
  );
}

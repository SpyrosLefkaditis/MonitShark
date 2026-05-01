import { isAxiosError } from "axios";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { AddRuleDialog } from "@/components/firewall/AddRuleDialog";
import { FirewallStatusCard } from "@/components/firewall/FirewallStatusCard";
import { RulesTable } from "@/components/firewall/RulesTable";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  useFirewallAddRule,
  useFirewallDeleteRule,
  useFirewallDisable,
  useFirewallEnable,
  useFirewallStatus,
} from "@/hooks/useFirewall";
import type { FirewallRule, FirewallRuleInput } from "@/types";

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

export function FirewallPage() {
  const { data: status, isLoading, error } = useFirewallStatus();
  const enable = useFirewallEnable();
  const disable = useFirewallDisable();
  const addRule = useFirewallAddRule();
  const deleteRule = useFirewallDeleteRule();

  const [addOpen, setAddOpen] = useState(false);
  const [toggleTarget, setToggleTarget] = useState<"enable" | "disable" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ rule: FirewallRule; n: number } | null>(null);

  const installed = status?.installed ?? false;
  const active = installed && (status?.active ?? false);
  const rules = status?.rules ?? [];

  const togglePending = enable.isPending || disable.isPending;

  const onConfirmToggle = async () => {
    if (!toggleTarget) return;
    try {
      const res =
        toggleTarget === "enable"
          ? await enable.mutateAsync()
          : await disable.mutateAsync();
      if (res.ok) {
        toast.success(`Firewall ${toggleTarget === "enable" ? "enabled" : "disabled"}.`, {
          description: res.output ? res.output.slice(0, 200) : undefined,
        });
      } else {
        toast.error("Firewall command failed.", {
          description: res.output ? res.output.slice(0, 200) : undefined,
        });
      }
    } catch (e) {
      toast.error("Firewall command failed.", { description: describeError(e) });
    } finally {
      setToggleTarget(null);
    }
  };

  const onAddRule = async (values: FirewallRuleInput) => {
    try {
      const res = await addRule.mutateAsync(values);
      if (res.ok) {
        toast.success("Rule added.", {
          description: res.output ? res.output.slice(0, 200) : undefined,
        });
        setAddOpen(false);
      } else {
        toast.error("Failed to add rule.", {
          description: res.output ? res.output.slice(0, 200) : undefined,
        });
      }
    } catch (e) {
      toast.error("Failed to add rule.", { description: describeError(e) });
    }
  };

  const onConfirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      const res = await deleteRule.mutateAsync(deleteTarget.n);
      if (res.ok) {
        toast.success(`Rule ${deleteTarget.n} deleted.`);
      } else {
        toast.error("Failed to delete rule.", {
          description: res.output ? res.output.slice(0, 200) : undefined,
        });
      }
    } catch (e) {
      toast.error("Failed to delete rule.", { description: describeError(e) });
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="grid gap-4">
      {isLoading ? (
        <Skeleton className="h-32" />
      ) : error ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-destructive">
            Failed to load firewall status. {describeError(error)}
          </CardContent>
        </Card>
      ) : (
        <FirewallStatusCard
          status={status}
          onToggle={(next) => setToggleTarget(next)}
          pending={togglePending}
        />
      )}

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Rules</CardTitle>
          <Button
            size="sm"
            disabled={!installed}
            onClick={() => setAddOpen(true)}
            className="gap-1.5"
          >
            <Plus className="size-4" />
            New rule
          </Button>
        </CardHeader>
        <CardContent>
          {!installed ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              UFW is not installed on this host.
            </div>
          ) : isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : (
            <RulesTable
              rules={rules}
              onDelete={(rule, n) => setDeleteTarget({ rule, n })}
            />
          )}
        </CardContent>
      </Card>

      <AddRuleDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onSubmit={onAddRule}
        pending={addRule.isPending}
      />

      <Dialog
        open={!!toggleTarget}
        onOpenChange={(o) => !o && setToggleTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {toggleTarget === "enable" ? "Enable firewall?" : "Disable firewall?"}
            </DialogTitle>
            <DialogDescription>
              {toggleTarget === "enable"
                ? "Activating UFW will enforce the configured default policies. Existing connections may be impacted if default-incoming is deny."
                : "Disabling UFW will stop enforcing all rules. The host will accept any inbound traffic not blocked elsewhere."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setToggleTarget(null)}
              disabled={togglePending}
            >
              Cancel
            </Button>
            <Button
              variant={toggleTarget === "disable" ? "destructive" : "default"}
              onClick={onConfirmToggle}
              disabled={togglePending}
            >
              {togglePending
                ? "Working…"
                : toggleTarget === "enable"
                ? "Enable firewall"
                : "Disable firewall"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete rule {deleteTarget?.n}?</DialogTitle>
            <DialogDescription>
              This removes the rule from the active firewall configuration.
              {active ? "" : " (Firewall is currently inactive — the rule will still be removed from the saved config.)"}
            </DialogDescription>
          </DialogHeader>
          {deleteTarget && (
            <div className="rounded-md border border-border bg-muted/40 p-3 space-y-1 text-xs font-mono">
              <div>
                <span className="text-muted-foreground">to:</span> {deleteTarget.rule.to}
              </div>
              <div>
                <span className="text-muted-foreground">from:</span> {deleteTarget.rule.from}
              </div>
              <div>
                <span className="text-muted-foreground">action:</span> {deleteTarget.rule.action}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={deleteRule.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={onConfirmDelete}
              disabled={deleteRule.isPending}
            >
              {deleteRule.isPending ? "Deleting…" : "Delete rule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

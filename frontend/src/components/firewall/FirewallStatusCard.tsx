import { Power, ShieldCheck, ShieldOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FirewallStatus } from "@/types";

type Props = {
  status: FirewallStatus | undefined;
  onToggle: (next: "enable" | "disable") => void;
  pending?: boolean;
};

export function FirewallStatusCard({ status, onToggle, pending }: Props) {
  const installed = status?.installed ?? false;
  const active = installed && (status?.active ?? false);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
        <div className="flex items-center gap-2">
          {active ? (
            <ShieldCheck className="size-5 text-emerald-400" />
          ) : (
            <ShieldOff className="size-5 text-muted-foreground" />
          )}
          <CardTitle className="text-base">Firewall</CardTitle>
          {installed ? (
            <Badge variant={active ? "success" : "outline"} className="uppercase tracking-wide">
              {active ? "Active" : "Inactive"}
            </Badge>
          ) : (
            <Badge variant="warning">Not installed</Badge>
          )}
        </div>
        {installed && (
          <Button
            size="sm"
            variant={active ? "destructive" : "default"}
            disabled={pending}
            onClick={() => onToggle(active ? "disable" : "enable")}
            className="gap-1.5"
          >
            <Power className="size-4" />
            {pending ? "Working…" : active ? "Disable" : "Enable"}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {!installed ? (
          <p className="text-sm text-muted-foreground">
            UFW is not installed on this host. Install <span className="font-mono">ufw</span> with
            your distro's package manager to manage firewall rules from here.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <Policy label="Default incoming" value={status?.default_incoming ?? "—"} />
            <Policy label="Default outgoing" value={status?.default_outgoing ?? "—"} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Policy({ label, value }: { label: string; value: string }) {
  const v = (value || "").toLowerCase();
  const variant: "success" | "destructive" | "warning" | "outline" =
    v === "allow" ? "success" : v === "deny" ? "destructive" : v === "reject" ? "warning" : "outline";
  return (
    <div className="rounded-md border border-border px-3 py-2 flex items-center justify-between">
      <span className="text-muted-foreground text-xs uppercase tracking-wide">{label}</span>
      <Badge variant={variant} className="font-mono uppercase">
        {value || "—"}
      </Badge>
    </div>
  );
}

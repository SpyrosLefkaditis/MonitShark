import { Loader2, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  onRun: () => void;
  pending: boolean;
  totalFindings: number | null;
  lastRunAt: number | null;
};

export function AuditRunner({ onRun, pending, totalFindings, lastRunAt }: Props) {
  return (
    <div className="flex items-center justify-between gap-4 flex-wrap">
      <div className="flex items-center gap-3">
        <div className="size-9 rounded-md bg-primary/15 grid place-items-center text-primary">
          <ShieldCheck className="size-4" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">Security audits</div>
          <div className="text-xs text-muted-foreground leading-tight">
            {lastRunAt
              ? `Last run ${new Date(lastRunAt).toLocaleString()} · ${totalFindings ?? 0} findings`
              : "Run all built-in checks: SSH, users, permissions, packages."}
          </div>
        </div>
      </div>
      <Button onClick={onRun} disabled={pending} className="gap-2">
        {pending ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
        {pending ? "Running…" : "Run full audit"}
      </Button>
    </div>
  );
}

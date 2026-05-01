import { BellOff, Check } from "lucide-react";

import { useAckAlert, useAlerts } from "@/hooks/useAlerts";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTimestamp } from "@/lib/format";
import type { Severity } from "@/types";

function sevVariant(sev: Severity): BadgeProps["variant"] {
  switch (sev) {
    case "critical":
    case "high":
      return "destructive";
    case "medium":
      return "warning";
    case "low":
      return "secondary";
    case "info":
    default:
      return "outline";
  }
}

export function AlertsList() {
  const { data, isLoading } = useAlerts("open");
  const ack = useAckAlert();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    );
  }

  const alerts = data ?? [];
  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-8 gap-2 text-muted-foreground">
        <BellOff className="size-6" />
        <div className="text-sm">No open alerts.</div>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border max-h-[26rem] overflow-y-auto">
      {alerts.map((a) => (
        <div key={a.id} className="py-2 flex items-start gap-3">
          <Badge variant={sevVariant(a.severity)} className="uppercase text-[10px] tracking-wide mt-0.5 shrink-0">
            {a.severity}
          </Badge>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium leading-tight truncate">{a.title}</div>
            <div className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{a.body}</div>
            <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
              {formatTimestamp(a.created_at)}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            title="Acknowledge"
            onClick={() => ack.mutate(a.id)}
            disabled={ack.isPending}
            className="shrink-0"
          >
            <Check className="size-4" />
          </Button>
        </div>
      ))}
    </div>
  );
}

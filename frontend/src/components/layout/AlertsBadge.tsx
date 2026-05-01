import { Bell } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function AlertsBadge() {
  // Phase 3 wires this to useAlerts() and live alerts from /api/alerts.
  const count = 0;
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground" data-testid="alerts-badge">
      <Bell className="size-4" />
      <Badge variant={count > 0 ? "destructive" : "outline"} className="font-mono">
        {count}
      </Badge>
    </div>
  );
}

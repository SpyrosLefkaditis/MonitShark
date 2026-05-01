import { Bell } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useAlerts } from "@/hooks/useAlerts";

export function AlertsBadge() {
  const { data } = useAlerts("open");
  const count = data?.length ?? 0;
  return (
    <div
      className="flex items-center gap-1.5 text-xs text-muted-foreground"
      data-testid="alerts-badge"
    >
      <Bell className="size-4" />
      <Badge variant={count > 0 ? "destructive" : "outline"} className="font-mono">
        {count}
      </Badge>
    </div>
  );
}

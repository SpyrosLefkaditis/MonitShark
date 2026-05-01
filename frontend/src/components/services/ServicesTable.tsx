import { Pause, Play, RefreshCw, RotateCcw } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { ServiceAction, ServiceItem } from "@/types";

function stateVariant(active: string): BadgeProps["variant"] {
  if (active === "active") return "success";
  if (active === "failed") return "destructive";
  if (active === "activating" || active === "deactivating") return "warning";
  return "outline";
}

type Props = {
  services: ServiceItem[];
  onAction: (svc: ServiceItem, action: ServiceAction) => void;
};

export function ServicesTable({ services, onAction }: Props) {
  if (services.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        No services match the current filter.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-2 px-3 font-medium">Name</th>
            <th className="py-2 px-3 font-medium">Description</th>
            <th className="py-2 px-3 font-medium">State</th>
            <th className="py-2 px-3 font-medium">Enabled</th>
            <th className="py-2 px-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {services.map((s) => {
            const isActive = s.active_state === "active";
            return (
              <tr key={s.name} className="border-b border-border/60 last:border-b-0 hover:bg-accent/40">
                <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{s.name}</td>
                <td className="py-2 px-3 text-muted-foreground max-w-[28rem] truncate" title={s.description}>
                  {s.description || "—"}
                </td>
                <td className="py-2 px-3">
                  <div className="flex items-center gap-1.5">
                    <Badge variant={stateVariant(s.active_state)} className="text-[10px] uppercase tracking-wide">
                      {s.active_state}
                    </Badge>
                    {s.sub_state && s.sub_state !== s.active_state && (
                      <span className="text-[11px] text-muted-foreground font-mono">
                        ({s.sub_state})
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-2 px-3">
                  <span
                    className={cn(
                      "text-xs font-mono",
                      s.enabled === "enabled" ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {s.enabled ?? "—"}
                  </span>
                </td>
                <td className="py-2 px-3">
                  <div className="flex items-center justify-end gap-1">
                    {!isActive && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="size-7"
                            onClick={() => onAction(s, "start")}
                            aria-label="Start"
                          >
                            <Play className="size-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Start</TooltipContent>
                      </Tooltip>
                    )}
                    {isActive && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="size-7"
                            onClick={() => onAction(s, "stop")}
                            aria-label="Stop"
                          >
                            <Pause className="size-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Stop</TooltipContent>
                      </Tooltip>
                    )}
                    {isActive && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="size-7"
                            onClick={() => onAction(s, "restart")}
                            aria-label="Restart"
                          >
                            <RotateCcw className="size-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Restart</TooltipContent>
                      </Tooltip>
                    )}
                    {isActive && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="size-7"
                            onClick={() => onAction(s, "reload")}
                            aria-label="Reload"
                          >
                            <RefreshCw className="size-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Reload</TooltipContent>
                      </Tooltip>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

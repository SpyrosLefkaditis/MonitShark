import { Trash2 } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { FirewallAction, FirewallRule } from "@/types";

function actionVariant(a: FirewallAction): BadgeProps["variant"] {
  if (a === "ALLOW") return "success";
  if (a === "DENY" || a === "REJECT") return "destructive";
  if (a === "LIMIT") return "warning";
  return "outline";
}

type Props = {
  rules: FirewallRule[];
  onDelete: (rule: FirewallRule, ruleNumber: number) => void;
};

export function RulesTable({ rules, onDelete }: Props) {
  if (rules.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        No firewall rules yet. Click "New rule" to add one.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-2 px-3 font-medium w-10">#</th>
            <th className="py-2 px-3 font-medium">To</th>
            <th className="py-2 px-3 font-medium">From</th>
            <th className="py-2 px-3 font-medium">Proto</th>
            <th className="py-2 px-3 font-medium">Action</th>
            <th className="py-2 px-3 font-medium">Comment</th>
            <th className="py-2 px-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r, idx) => {
            const num = idx + 1;
            return (
              <tr
                key={`${num}-${r.to}-${r.from}-${r.action}`}
                className="border-b border-border/60 last:border-b-0 hover:bg-accent/40"
              >
                <td className="py-2 px-3 font-mono text-xs">{num}</td>
                <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{r.to}</td>
                <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{r.from}</td>
                <td className="py-2 px-3">
                  {r.proto ? (
                    <Badge variant="outline" className="font-mono uppercase">
                      {r.proto}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="py-2 px-3">
                  <Badge variant={actionVariant(r.action)} className="font-mono">
                    {r.action}
                  </Badge>
                </td>
                <td className="py-2 px-3 text-xs text-muted-foreground max-w-[16rem] truncate" title={r.comment ?? ""}>
                  {r.comment ?? "—"}
                </td>
                <td className="py-2 px-3">
                  <div className="flex items-center justify-end">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="icon"
                          className="size-7"
                          onClick={() => onDelete(r, num)}
                          aria-label="Delete rule"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Delete rule</TooltipContent>
                    </Tooltip>
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

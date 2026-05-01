import { AlertTriangle, Check, X } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  action: string;
  args: unknown;
  summary: string;
  risk: string;
  decision: "pending" | "approve" | "deny";
  onDecide: (decision: "approve" | "deny") => void;
};

function riskVariant(risk: string): BadgeProps["variant"] {
  const r = risk.toLowerCase();
  if (r.includes("high") || r.includes("critical")) return "destructive";
  if (r.includes("medium") || r.includes("warn")) return "warning";
  return "secondary";
}

function pretty(value: unknown): string {
  if (value === undefined || value === null) return "(none)";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ConfirmationCard({ action, args, summary, risk, decision, onDecide }: Props) {
  const isResolved = decision !== "pending";
  return (
    <div className="rounded-lg border-2 border-amber-500/50 bg-amber-500/5">
      <div className="flex items-start gap-2 px-3 py-2 border-b border-amber-500/30">
        <div className="size-6 rounded bg-amber-500/20 grid place-items-center text-amber-500 shrink-0 mt-0.5">
          <AlertTriangle className="size-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs">{action}</span>
            <Badge variant={riskVariant(risk)} className="text-[10px] uppercase tracking-wide">
              {risk}
            </Badge>
          </div>
          <p className="text-sm mt-1">{summary}</p>
        </div>
      </div>
      <div className="p-2">
        <details className="group">
          <summary className="cursor-pointer text-xs text-muted-foreground select-none">
            Arguments
          </summary>
          <pre className={cn("mt-1.5 max-h-48 overflow-auto rounded border border-border bg-card p-2 text-[11px] font-mono leading-snug")}>
            {pretty(args)}
          </pre>
        </details>
      </div>
      <div className="px-3 pb-3 flex items-center gap-2">
        {!isResolved ? (
          <>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onDecide("deny")}
              className="gap-1.5"
            >
              <X className="size-3.5" />
              Deny
            </Button>
            <Button size="sm" onClick={() => onDecide("approve")} className="gap-1.5">
              <Check className="size-3.5" />
              Allow
            </Button>
          </>
        ) : (
          <Badge variant={decision === "approve" ? "success" : "destructive"}>
            {decision === "approve" ? "Approved" : "Denied"}
          </Badge>
        )}
      </div>
    </div>
  );
}

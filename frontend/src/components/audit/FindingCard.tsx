import { Loader2, Wrench, X } from "lucide-react";

import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Finding, Severity } from "@/types";

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

type Props = {
  finding: Finding;
  onApply: () => void;
  onDismiss: () => void;
  applyPending?: boolean;
  dismissPending?: boolean;
};

export function FindingCard({ finding, onApply, onDismiss, applyPending, dismissPending }: Props) {
  const evidenceJson = (() => {
    try {
      return JSON.stringify(finding.evidence, null, 2);
    } catch {
      return String(finding.evidence);
    }
  })();
  const evidenceEmpty = !finding.evidence || Object.keys(finding.evidence).length === 0;
  const isFixed = finding.status === "fixed";
  const isDismissed = finding.status === "dismissed";

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex items-start gap-3 p-3 border-b border-border">
        <Badge variant={sevVariant(finding.severity)} className="uppercase text-[10px] tracking-wide mt-0.5 shrink-0">
          {finding.severity}
        </Badge>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium leading-snug">{finding.title}</div>
          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
            {finding.category} · {finding.id}
            {finding.fix_id && ` · fix:${finding.fix_id}`}
          </div>
        </div>
        {isFixed && <Badge variant="success">Fixed</Badge>}
        {isDismissed && <Badge variant="outline">Dismissed</Badge>}
      </div>
      <div className="p-3 text-sm">
        <MarkdownRenderer source={finding.description || "_No description._"} />
      </div>
      {!evidenceEmpty && (
        <div className="px-3 pb-3">
          <details className="rounded-md border border-border bg-muted/40">
            <summary className="cursor-pointer select-none px-2 py-1.5 text-xs text-muted-foreground">
              Evidence
            </summary>
            <pre className="px-2 pb-2 text-[11px] font-mono leading-snug overflow-x-auto whitespace-pre-wrap break-all">
              {evidenceJson}
            </pre>
          </details>
        </div>
      )}
      {finding.status === "open" && (
        <div className="px-3 pb-3 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onApply}
            disabled={applyPending || !finding.fix_id}
            className="gap-1.5"
            title={
              finding.fix_id
                ? "Apply the suggested fix (Phase 7 wires real fixes)."
                : "No fix wired for this finding."
            }
          >
            {applyPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Wrench className="size-3.5" />
            )}
            Apply fix
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onDismiss}
            disabled={dismissPending}
            className="gap-1.5"
          >
            <X className="size-3.5" />
            Dismiss
          </Button>
        </div>
      )}
    </div>
  );
}

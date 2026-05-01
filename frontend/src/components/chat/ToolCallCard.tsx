import { CheckCircle2, Loader2, Wrench, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Props = {
  name: string;
  args: unknown;
  status: "running" | "done";
  ok?: boolean;
  output?: unknown;
};

function pretty(value: unknown): string {
  if (value === undefined) return "(none)";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ToolCallCard({ name, args, status, ok, output }: Props) {
  const isDone = status === "done";
  return (
    <div className="rounded-lg border border-border bg-muted/30">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2 min-w-0">
          <div className="size-6 rounded bg-primary/15 grid place-items-center text-primary shrink-0">
            <Wrench className="size-3.5" />
          </div>
          <span className="font-mono text-xs truncate">{name}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {!isDone && (
            <Badge variant="secondary" className="gap-1">
              <Loader2 className="size-3 animate-spin" />
              <span>running</span>
            </Badge>
          )}
          {isDone && ok && (
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="size-3" />
              <span>done</span>
            </Badge>
          )}
          {isDone && !ok && (
            <Badge variant="destructive" className="gap-1">
              <XCircle className="size-3" />
              <span>error</span>
            </Badge>
          )}
        </div>
      </div>
      <div className="p-2 space-y-1">
        <details className="group">
          <summary className="cursor-pointer text-xs text-muted-foreground select-none">
            Arguments
          </summary>
          <pre
            className={cn(
              "mt-1.5 max-h-48 overflow-auto rounded border border-border bg-card p-2",
              "text-[11px] font-mono leading-snug",
            )}
          >
            {pretty(args)}
          </pre>
        </details>
        {isDone && (
          <details className="group" open>
            <summary className="cursor-pointer text-xs text-muted-foreground select-none">
              Result
            </summary>
            <pre
              className={cn(
                "mt-1.5 max-h-64 overflow-auto rounded border border-border bg-card p-2",
                "text-[11px] font-mono leading-snug",
              )}
            >
              {pretty(output)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}

import { type Finding } from "@/types";

import { FindingCard } from "./FindingCard";

type Props = {
  category: string;
  findings: Finding[];
  onApply: (id: string) => void;
  onDismiss: (id: string) => void;
  applyingId?: string | null;
  dismissingId?: string | null;
};

export function FindingsGroup({
  category,
  findings,
  onApply,
  onDismiss,
  applyingId,
  dismissingId,
}: Props) {
  if (findings.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        No findings in <span className="font-mono">{category}</span>.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {findings.map((f) => (
        <FindingCard
          key={f.id}
          finding={f}
          onApply={() => onApply(f.id)}
          onDismiss={() => onDismiss(f.id)}
          applyPending={applyingId === f.id}
          dismissPending={dismissingId === f.id}
        />
      ))}
    </div>
  );
}

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export type ApplyKind = "security" | "all";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  kind: ApplyKind | null;
  onConfirm: () => void;
  pending?: boolean;
};

const TEXT: Record<ApplyKind, { title: string; description: string; cta: string }> = {
  security: {
    title: "Apply security updates?",
    description:
      "This applies only the security-flagged updates. The operation can take several minutes and may restart background services. Active users could see brief interruptions.",
    cta: "Apply security",
  },
  all: {
    title: "Apply all updates?",
    description:
      "This applies every pending update, security and otherwise. The operation can take a long time, will restart updated services, and may pull in new package versions. Confirm only on a window where short service interruptions are acceptable.",
    cta: "Apply all",
  },
};

export function ApplyUpdatesDialog({ open, onOpenChange, kind, onConfirm, pending }: Props) {
  if (!kind) return null;
  const t = TEXT[kind];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.title}</DialogTitle>
          <DialogDescription>{t.description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button
            variant={kind === "all" ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? "Working…" : t.cta}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

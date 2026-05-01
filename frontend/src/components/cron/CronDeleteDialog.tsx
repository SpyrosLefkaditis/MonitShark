import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CronEntry } from "@/types";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry: CronEntry | null;
  onConfirm: () => void;
  pending?: boolean;
};

export function CronDeleteDialog({ open, onOpenChange, entry, onConfirm, pending }: Props) {
  if (!entry) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete cron job?</DialogTitle>
          <DialogDescription>
            This will remove the entry from <span className="font-mono">{entry.user}</span>'s
            crontab. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md border border-border bg-muted/40 p-3 space-y-1 text-xs font-mono">
          <div>
            <span className="text-muted-foreground">schedule:</span> {entry.schedule}
          </div>
          <div className="break-all">
            <span className="text-muted-foreground">command:</span> {entry.command}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={pending}>
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

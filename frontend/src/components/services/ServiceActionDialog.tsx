import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ServiceAction } from "@/types";

const ACTION_TEXT: Record<ServiceAction, { verb: string; warning: string }> = {
  start: { verb: "Start", warning: "Bring this unit online." },
  stop: { verb: "Stop", warning: "This will halt the service and may interrupt clients." },
  restart: {
    verb: "Restart",
    warning: "This will briefly interrupt the service. Active connections may drop.",
  },
  reload: {
    verb: "Reload",
    warning: "Reload configuration without a restart (graceful for most services).",
  },
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  service: string | null;
  action: ServiceAction | null;
  onConfirm: () => void;
  pending?: boolean;
};

export function ServiceActionDialog({
  open,
  onOpenChange,
  service,
  action,
  onConfirm,
  pending,
}: Props) {
  if (!service || !action) return null;
  const { verb, warning } = ACTION_TEXT[action];
  const isDestructive = action === "stop" || action === "restart";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {verb} <span className="font-mono">{service}</span>?
          </DialogTitle>
          <DialogDescription>{warning}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button
            variant={isDestructive ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? `${verb}ing…` : `Confirm ${verb}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

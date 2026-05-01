import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { CronEntry } from "@/types";

export type CronFormValues = {
  user: string;
  schedule: string;
  command: string;
  comment: string;
  enabled: boolean;
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: CronEntry | null;
  onSubmit: (values: CronFormValues) => void;
  pending?: boolean;
};

const SCHEDULE_PATTERN =
  /^(\@(reboot|hourly|daily|weekly|monthly|yearly|annually))|((\S+\s+){4}\S+)$/;

export function CronFormDialog({ open, onOpenChange, initial, onSubmit, pending }: Props) {
  const isEdit = !!initial;
  const [user, setUser] = useState("root");
  const [schedule, setSchedule] = useState("0 * * * *");
  const [command, setCommand] = useState("");
  const [comment, setComment] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setUser(initial?.user ?? "root");
      setSchedule(initial?.schedule ?? "0 * * * *");
      setCommand(initial?.command ?? "");
      setComment(initial?.comment ?? "");
      setEnabled(initial ? initial.enabled : true);
      setScheduleError(null);
    }
  }, [open, initial]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!SCHEDULE_PATTERN.test(schedule.trim())) {
      setScheduleError(
        "Use 5 space-separated cron fields (e.g. \"0 * * * *\") or @daily/@hourly/etc.",
      );
      return;
    }
    if (!command.trim()) return;
    setScheduleError(null);
    onSubmit({
      user: user.trim() || "root",
      schedule: schedule.trim(),
      command: command.trim(),
      comment: comment.trim(),
      enabled,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit cron job" : "New cron job"}</DialogTitle>
          <DialogDescription>
            Schedules use standard cron syntax (minute hour day month dow) or @-aliases.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="cron-user">User</Label>
              <Input
                id="cron-user"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                disabled={isEdit}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cron-schedule">Schedule</Label>
              <Input
                id="cron-schedule"
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                className="font-mono"
                required
              />
              {scheduleError && (
                <p className="text-[11px] text-destructive">{scheduleError}</p>
              )}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cron-command">Command</Label>
            <Textarea
              id="cron-command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              className="font-mono text-xs"
              rows={3}
              required
              placeholder="/usr/local/bin/backup.sh --quiet"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cron-comment">Comment (optional)</Label>
            <Input
              id="cron-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Nightly backup"
            />
          </div>
          {isEdit && (
            <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <Label htmlFor="cron-enabled" className="text-sm">
                Enabled
              </Label>
              <Switch
                id="cron-enabled"
                checked={enabled}
                onCheckedChange={setEnabled}
              />
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : isEdit ? "Save changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

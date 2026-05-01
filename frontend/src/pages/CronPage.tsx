import { isAxiosError } from "axios";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { CronDeleteDialog } from "@/components/cron/CronDeleteDialog";
import { CronFormDialog, type CronFormValues } from "@/components/cron/CronFormDialog";
import { CronTable } from "@/components/cron/CronTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCronCreate,
  useCronDelete,
  useCronJobs,
  useCronRun,
  useCronUpdate,
} from "@/hooks/useCron";
import type { CronEntry } from "@/types";

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

export function CronPage() {
  const { data, isLoading, error } = useCronJobs();
  const create = useCronCreate();
  const update = useCronUpdate();
  const remove = useCronDelete();
  const run = useCronRun();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<CronEntry | null>(null);
  const [deleting, setDeleting] = useState<CronEntry | null>(null);

  const onCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const onEdit = (entry: CronEntry) => {
    setEditing(entry);
    setFormOpen(true);
  };

  const onSubmit = async (values: CronFormValues) => {
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          body: {
            schedule: values.schedule,
            command: values.command,
            comment: values.comment || null,
            enabled: values.enabled,
          },
        });
        toast.success("Cron job updated.");
      } else {
        await create.mutateAsync({
          user: values.user,
          schedule: values.schedule,
          command: values.command,
          comment: values.comment || null,
        });
        toast.success("Cron job created.");
      }
      setFormOpen(false);
      setEditing(null);
    } catch (e) {
      toast.error("Failed to save cron job.", { description: describeError(e) });
    }
  };

  const onDelete = async () => {
    if (!deleting) return;
    try {
      await remove.mutateAsync(deleting.id);
      toast.success("Cron job deleted.");
      setDeleting(null);
    } catch (e) {
      toast.error("Failed to delete cron job.", { description: describeError(e) });
    }
  };

  const onRun = async (entry: CronEntry) => {
    // Split command into argv. Quoting is best-effort; complex shell pipelines won't round-trip.
    const parts = entry.command.match(/(?:[^\s"]+|"[^"]*")+/g) ?? [];
    const argv = parts.map((p) => p.replace(/^"|"$/g, ""));
    if (argv.length === 0) {
      toast.error("Empty command.");
      return;
    }
    try {
      const r = await run.mutateAsync({
        command: argv[0],
        args: argv.slice(1),
        timeout_s: 30,
      });
      const desc =
        (r.stdout ? r.stdout.slice(0, 200) : "") +
        (r.stderr ? `\nstderr: ${r.stderr.slice(0, 200)}` : "");
      if (r.rc === 0) {
        toast.success(`Run completed (rc=0)`, { description: desc || undefined });
      } else {
        toast.error(`Run finished rc=${r.rc}`, { description: desc || undefined });
      }
    } catch (e) {
      toast.error("Failed to run command.", { description: describeError(e) });
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Cron jobs</CardTitle>
          <Button size="sm" onClick={onCreate} className="gap-1.5">
            <Plus className="size-4" />
            New cron job
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : error ? (
            <div className="py-10 text-center text-sm text-destructive">
              Failed to load cron jobs. {(error as Error).message}
            </div>
          ) : (
            <CronTable
              entries={data ?? []}
              onRun={onRun}
              onEdit={onEdit}
              onDelete={(e) => setDeleting(e)}
            />
          )}
        </CardContent>
      </Card>

      <CronFormDialog
        open={formOpen}
        onOpenChange={(o) => {
          setFormOpen(o);
          if (!o) setEditing(null);
        }}
        initial={editing}
        onSubmit={onSubmit}
        pending={create.isPending || update.isPending}
      />

      <CronDeleteDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        entry={deleting}
        onConfirm={onDelete}
        pending={remove.isPending}
      />
    </div>
  );
}

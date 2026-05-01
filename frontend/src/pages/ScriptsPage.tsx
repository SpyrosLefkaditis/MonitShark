import { isAxiosError } from "axios";
import { Calendar, FileCode, FilePlus2, Play, Save, Server, Trash2 } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  useDeleteScript,
  useInstallScriptService,
  useRunScript,
  useSaveScript,
  useScheduleScript,
  useScript,
  useScripts,
} from "@/hooks/useScripts";
import { cn } from "@/lib/utils";
import type { ScriptRunResult } from "@/types";

const NAME_RE = /^[a-zA-Z0-9_-]{1,64}$/;
const SERVICE_NAME_RE = /^[a-zA-Z0-9_.-]+$/;
const RESTART_VALUES = ["no", "always", "on-failure", "on-abnormal"] as const;
type RestartValue = (typeof RESTART_VALUES)[number];

const TEMPLATE_CONTENT = `#!/usr/bin/env bash
set -euo pipefail

echo "hello from $(hostname) at $(date -Iseconds)"
`;

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

function formatTs(ts: number): string {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString();
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function ScriptsPage() {
  const list = useScripts();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useScript(selected);

  const save = useSaveScript();
  const remove = useDeleteScript();
  const run = useRunScript();
  const installService = useInstallScriptService();
  const schedule = useScheduleScript();

  const [editorContent, setEditorContent] = useState<string>("");
  const [editorExecutable, setEditorExecutable] = useState<boolean>(true);
  const [dirty, setDirty] = useState<boolean>(false);
  const [lastRun, setLastRun] = useState<ScriptRunResult | null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [installOpen, setInstallOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // When backend content arrives, sync the editor.
  useEffect(() => {
    if (detail.data && detail.data.name === selected) {
      setEditorContent(detail.data.content);
      setDirty(false);
    }
  }, [detail.data, selected]);

  // Auto-select first on initial load.
  useEffect(() => {
    if (!selected && list.data && list.data.length > 0) {
      setSelected(list.data[0].name);
    }
  }, [selected, list.data]);

  const sortedScripts = useMemo(
    () => [...(list.data ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [list.data],
  );

  const onSave = async () => {
    if (!selected) return;
    try {
      await save.mutateAsync({
        name: selected,
        content: editorContent,
        make_executable: editorExecutable,
      });
      setDirty(false);
      toast.success(`Saved ${selected}.sh`);
    } catch (e) {
      toast.error("Failed to save script.", { description: describeError(e) });
    }
  };

  const onCreate = async (name: string) => {
    if (!NAME_RE.test(name)) {
      toast.error("Invalid name. Use letters, digits, _ or - (max 64).");
      return;
    }
    try {
      await save.mutateAsync({
        name,
        content: TEMPLATE_CONTENT,
        make_executable: true,
      });
      setSelected(name);
      setNewOpen(false);
      toast.success(`Created ${name}.sh`);
    } catch (e) {
      toast.error("Failed to create script.", { description: describeError(e) });
    }
  };

  const onDelete = async () => {
    if (!deleteTarget) return;
    try {
      await remove.mutateAsync(deleteTarget);
      toast.success(`Deleted ${deleteTarget}.sh`);
      if (selected === deleteTarget) {
        setSelected(null);
        setEditorContent("");
      }
      setDeleteTarget(null);
    } catch (e) {
      toast.error("Failed to delete script.", { description: describeError(e) });
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Scripts</CardTitle>
          <Button size="sm" onClick={() => setNewOpen(true)} className="gap-1.5">
            <FilePlus2 className="size-4" />
            New script
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-[260px_1fr]">
            <div className="space-y-2">
              {list.isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-9" />
                ))
              ) : sortedScripts.length === 0 ? (
                <div className="text-sm text-muted-foreground py-6 text-center">
                  No scripts yet.
                </div>
              ) : (
                <ul className="space-y-1">
                  {sortedScripts.map((s) => (
                    <li key={s.name}>
                      <button
                        type="button"
                        onClick={() => setSelected(s.name)}
                        className={cn(
                          "w-full flex items-center justify-between gap-2 rounded-md border border-border px-2.5 py-2 text-left text-sm transition-colors",
                          selected === s.name
                            ? "bg-accent text-accent-foreground"
                            : "hover:bg-accent/60",
                        )}
                      >
                        <span className="flex items-center gap-2 min-w-0">
                          <FileCode className="size-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate font-mono text-xs">{s.name}</span>
                        </span>
                        <button
                          type="button"
                          aria-label="Delete script"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(s.name);
                          }}
                          className="text-muted-foreground hover:text-destructive p-1 -mr-1"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="min-w-0 space-y-3">
              {!selected ? (
                <div className="border border-dashed border-border rounded-md py-12 text-center text-sm text-muted-foreground">
                  Select a script on the left, or create a new one.
                </div>
              ) : detail.isLoading && !detail.data ? (
                <Skeleton className="h-[420px]" />
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-sm truncate">{selected}.sh</span>
                      <span className="text-xs text-muted-foreground">
                        {detail.data ? `modified ${formatTs(detail.data.modified_at)}` : ""}
                      </span>
                      {dirty && (
                        <span className="text-xs text-amber-500">(unsaved)</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 text-xs">
                        <Switch
                          id="exec"
                          checked={editorExecutable}
                          onCheckedChange={(v) => {
                            setEditorExecutable(v);
                            setDirty(true);
                          }}
                        />
                        <Label htmlFor="exec" className="cursor-pointer">
                          executable
                        </Label>
                      </div>
                      <Button
                        size="sm"
                        onClick={onSave}
                        disabled={save.isPending}
                        className="gap-1.5"
                      >
                        <Save className="size-4" />
                        Save
                      </Button>
                    </div>
                  </div>

                  <Textarea
                    rows={30}
                    value={editorContent}
                    onChange={(e) => {
                      setEditorContent(e.target.value);
                      setDirty(true);
                    }}
                    className="font-mono text-xs leading-relaxed"
                    spellCheck={false}
                  />

                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRunOpen(true)}
                      className="gap-1.5"
                    >
                      <Play className="size-3.5" />
                      Run
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setInstallOpen(true)}
                      className="gap-1.5"
                    >
                      <Server className="size-3.5" />
                      Install as service
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setScheduleOpen(true)}
                      className="gap-1.5"
                    >
                      <Calendar className="size-3.5" />
                      Schedule via cron
                    </Button>
                  </div>

                  {lastRun && (
                    <details
                      open
                      className="rounded-md border border-border bg-muted/40 p-3"
                    >
                      <summary className="cursor-pointer text-xs font-medium">
                        Last run · rc={lastRun.rc} · timeout {lastRun.timeout_s}s
                      </summary>
                      <div className="mt-2 grid gap-2">
                        <div>
                          <div className="text-[10px] uppercase text-muted-foreground tracking-wider">
                            stdout
                          </div>
                          <pre className="font-mono text-xs whitespace-pre-wrap break-all bg-background border border-border rounded p-2 max-h-64 overflow-auto">
                            {lastRun.stdout || "(empty)"}
                          </pre>
                        </div>
                        {lastRun.stderr && (
                          <div>
                            <div className="text-[10px] uppercase text-muted-foreground tracking-wider">
                              stderr
                            </div>
                            <pre className="font-mono text-xs whitespace-pre-wrap break-all bg-background border border-border rounded p-2 max-h-64 overflow-auto">
                              {lastRun.stderr}
                            </pre>
                          </div>
                        )}
                      </div>
                    </details>
                  )}

                  {detail.data && (
                    <div className="text-xs text-muted-foreground">
                      Path: <span className="font-mono">/opt/cockpit/scripts/{selected}.sh</span>
                      {(() => {
                        const meta = list.data?.find((s) => s.name === selected);
                        return meta ? ` · ${formatBytes(meta.size_bytes)}` : "";
                      })()}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <NewScriptDialog
        open={newOpen}
        onOpenChange={setNewOpen}
        onCreate={onCreate}
        pending={save.isPending}
      />

      <RunDialog
        open={runOpen}
        onOpenChange={setRunOpen}
        scriptName={selected}
        onRun={async (args, timeout_s) => {
          if (!selected) return;
          try {
            const r = await run.mutateAsync({ name: selected, args, timeout_s });
            setLastRun(r);
            setRunOpen(false);
            if (r.rc === 0) {
              toast.success(`Run completed (rc=0)`);
            } else {
              toast.error(`Run finished rc=${r.rc}`);
            }
          } catch (e) {
            toast.error("Run failed.", { description: describeError(e) });
          }
        }}
        pending={run.isPending}
      />

      <InstallServiceDialog
        open={installOpen}
        onOpenChange={setInstallOpen}
        scriptName={selected}
        onSubmit={async (svcName, description, restart) => {
          if (!selected) return;
          try {
            const r = await installService.mutateAsync({
              name: selected,
              service_name: svcName,
              description,
              restart,
            });
            setInstallOpen(false);
            toast.success(`Installed ${r.service}`, {
              description: r.unit_path,
            });
          } catch (e) {
            toast.error("Install failed.", { description: describeError(e) });
          }
        }}
        pending={installService.isPending}
      />

      <ScheduleDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        scriptName={selected}
        onSubmit={async (cronExpr, user) => {
          if (!selected) return;
          try {
            await schedule.mutateAsync({
              name: selected,
              schedule: cronExpr,
              user,
            });
            setScheduleOpen(false);
            toast.success(`Scheduled ${selected}.sh`, {
              description: `${cronExpr} as ${user}`,
            });
          } catch (e) {
            toast.error("Schedule failed.", { description: describeError(e) });
          }
        }}
        pending={schedule.isPending}
      />

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        name={deleteTarget}
        onConfirm={onDelete}
        pending={remove.isPending}
      />
    </div>
  );
}

type NewScriptDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreate: (name: string) => void;
  pending: boolean;
};

function NewScriptDialog({ open, onOpenChange, onCreate, pending }: NewScriptDialogProps) {
  const [name, setName] = useState("");
  useEffect(() => {
    if (open) setName("");
  }, [open]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onCreate(name.trim());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New script</DialogTitle>
          <DialogDescription>
            Creates an empty script under /opt/cockpit/scripts/. Allowed name
            characters: letters, digits, underscore, hyphen (max 64).
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="new-script-name">Name (no .sh suffix)</Label>
            <Input
              id="new-script-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-script"
              required
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending || !name.trim()}>
              {pending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type RunDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  scriptName: string | null;
  onRun: (args: string[], timeout_s: number) => void;
  pending: boolean;
};

function RunDialog({ open, onOpenChange, scriptName, onRun, pending }: RunDialogProps) {
  const [argsRaw, setArgsRaw] = useState("");
  const [timeout_s, setTimeoutS] = useState(60);

  useEffect(() => {
    if (open) {
      setArgsRaw("");
      setTimeoutS(60);
    }
  }, [open]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const args = argsRaw
      .split(/\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    onRun(args, timeout_s);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run {scriptName ?? ""}.sh</DialogTitle>
          <DialogDescription>
            Args are split on whitespace. Each arg must match
            <span className="font-mono"> [a-zA-Z0-9_./=:,@+-]+</span> (no shell metachars).
            Timeout capped at 300 seconds.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="run-args">Arguments</Label>
            <Input
              id="run-args"
              value={argsRaw}
              onChange={(e) => setArgsRaw(e.target.value)}
              placeholder="--flag value"
              className="font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="run-timeout">Timeout (seconds)</Label>
            <Input
              id="run-timeout"
              type="number"
              min={1}
              max={300}
              value={timeout_s}
              onChange={(e) => setTimeoutS(Number(e.target.value) || 60)}
              className="font-mono w-32"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Running..." : "Run"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type InstallServiceDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  scriptName: string | null;
  onSubmit: (serviceName: string, description: string, restart: RestartValue) => void;
  pending: boolean;
};

function InstallServiceDialog({
  open,
  onOpenChange,
  scriptName,
  onSubmit,
  pending,
}: InstallServiceDialogProps) {
  const [serviceName, setServiceName] = useState("");
  const [description, setDescription] = useState("");
  const [restart, setRestart] = useState<RestartValue>("no");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && scriptName) {
      setServiceName(`script-${scriptName}`);
      setDescription("");
      setRestart("no");
      setError(null);
    }
  }, [open, scriptName]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const name = serviceName.trim().replace(/\.service$/, "");
    if (!SERVICE_NAME_RE.test(name)) {
      setError("Service name must match [a-zA-Z0-9_.-]+");
      return;
    }
    setError(null);
    onSubmit(name, description.trim(), restart);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install {scriptName ?? ""}.sh as a systemd service</DialogTitle>
          <DialogDescription>
            Creates a oneshot unit at <span className="font-mono">/etc/systemd/system/</span>
            and reloads systemd. The unit is NOT started or enabled — use the Services page.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="svc-name">Service name (without .service)</Label>
            <Input
              id="svc-name"
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              required
              className="font-mono"
              placeholder="my-job"
            />
            {error && <p className="text-[11px] text-destructive">{error}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="svc-desc">Description (optional)</Label>
            <Input
              id="svc-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Daily database backup"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Restart policy</Label>
            <Select value={restart} onValueChange={(v) => setRestart(v as RestartValue)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RESTART_VALUES.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Installing..." : "Install"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type ScheduleDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  scriptName: string | null;
  onSubmit: (cronExpr: string, user: string) => void;
  pending: boolean;
};

const SCHEDULE_PATTERN =
  /^(\@(reboot|hourly|daily|weekly|monthly|yearly|annually))|((\S+\s+){4}\S+)$/;

function ScheduleDialog({
  open,
  onOpenChange,
  scriptName,
  onSubmit,
  pending,
}: ScheduleDialogProps) {
  const [cronExpr, setCronExpr] = useState("0 * * * *");
  const [user, setUser] = useState("root");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setCronExpr("0 * * * *");
      setUser("root");
      setError(null);
    }
  }, [open]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!SCHEDULE_PATTERN.test(cronExpr.trim())) {
      setError("Use 5 cron fields (e.g. \"0 * * * *\") or @daily/@hourly/etc.");
      return;
    }
    setError(null);
    onSubmit(cronExpr.trim(), user.trim() || "root");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule {scriptName ?? ""}.sh</DialogTitle>
          <DialogDescription>
            Adds a cron entry that runs the script on the host.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="sched-expr">Cron expression</Label>
            <Input
              id="sched-expr"
              value={cronExpr}
              onChange={(e) => setCronExpr(e.target.value)}
              required
              className="font-mono"
            />
            {error && <p className="text-[11px] text-destructive">{error}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="sched-user">User</Label>
            <Input
              id="sched-user"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              required
              className="font-mono"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Scheduling..." : "Schedule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type DeleteConfirmDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  name: string | null;
  onConfirm: () => void;
  pending: boolean;
};

function DeleteConfirmDialog({
  open,
  onOpenChange,
  name,
  onConfirm,
  pending,
}: DeleteConfirmDialogProps) {
  if (!name) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {name}.sh?</DialogTitle>
          <DialogDescription>
            Removes the file from /opt/cockpit/scripts/. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={pending}>
            {pending ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

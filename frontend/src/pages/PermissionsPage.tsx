import { isAxiosError } from "axios";
import {
  ArrowUp,
  File as FileIcon,
  FolderOpen,
  Link as LinkIcon,
} from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useChmod, useChown, useFsList } from "@/hooks/usePermissions";
import { cn } from "@/lib/utils";
import type { FsEntry } from "@/types";

const INITIAL_PATH = "/etc";
const ROOT_PATH = "/";

type PermBits = {
  ur: boolean;
  uw: boolean;
  ux: boolean;
  gr: boolean;
  gw: boolean;
  gx: boolean;
  or: boolean;
  ow: boolean;
  ox: boolean;
};

function octalToBits(octal: string): PermBits {
  const padded = octal.padStart(4, "0").slice(-3);
  const u = Number.parseInt(padded[0], 10);
  const g = Number.parseInt(padded[1], 10);
  const o = Number.parseInt(padded[2], 10);
  return {
    ur: (u & 4) !== 0,
    uw: (u & 2) !== 0,
    ux: (u & 1) !== 0,
    gr: (g & 4) !== 0,
    gw: (g & 2) !== 0,
    gx: (g & 1) !== 0,
    or: (o & 4) !== 0,
    ow: (o & 2) !== 0,
    ox: (o & 1) !== 0,
  };
}

function bitsToOctal(b: PermBits): string {
  const u = (b.ur ? 4 : 0) + (b.uw ? 2 : 0) + (b.ux ? 1 : 0);
  const g = (b.gr ? 4 : 0) + (b.gw ? 2 : 0) + (b.gx ? 1 : 0);
  const o = (b.or ? 4 : 0) + (b.ow ? 2 : 0) + (b.ox ? 1 : 0);
  return `${u}${g}${o}`;
}

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

function joinPath(base: string, name: string): string {
  if (base === ROOT_PATH) return `/${name}`;
  return `${base.replace(/\/$/, "")}/${name}`;
}

function parentOf(path: string): string {
  if (!path || path === ROOT_PATH) return ROOT_PATH;
  const trimmed = path.replace(/\/$/, "");
  const idx = trimmed.lastIndexOf("/");
  if (idx <= 0) return ROOT_PATH;
  return trimmed.slice(0, idx);
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTs(ts: number): string {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString();
}

function breadcrumbs(path: string): { label: string; full: string }[] {
  const out: { label: string; full: string }[] = [{ label: "/", full: ROOT_PATH }];
  if (!path || path === ROOT_PATH) return out;
  const parts = path.split("/").filter(Boolean);
  let acc = "";
  for (const p of parts) {
    acc = `${acc}/${p}`;
    out.push({ label: p, full: acc });
  }
  return out;
}

export function PermissionsPage() {
  const [path, setPath] = useState<string>(INITIAL_PATH);
  const listing = useFsList(path);

  const [selected, setSelected] = useState<FsEntry | null>(null);
  const [bits, setBits] = useState<PermBits>(() => octalToBits("644"));
  const [octal, setOctal] = useState<string>("644");
  const [chmodConfirmOpen, setChmodConfirmOpen] = useState(false);
  const [chownConfirmOpen, setChownConfirmOpen] = useState(false);
  const [owner, setOwner] = useState<string>("");
  const [group, setGroup] = useState<string>("");

  const chmod = useChmod();
  const chown = useChown();

  // When selecting a new entry, reset chmod/chown form fields.
  useEffect(() => {
    if (selected) {
      const o = selected.mode_octal.padStart(4, "0").slice(-3);
      setOctal(o);
      setBits(octalToBits(o));
      setOwner(selected.owner ?? "");
      setGroup(selected.group ?? "");
    }
  }, [selected]);

  // Re-sync selected when listing reloads (post-mutation).
  useEffect(() => {
    if (selected && listing.data) {
      const fresh = listing.data.entries.find((e) => e.name === selected.name);
      if (fresh && fresh.mode_octal !== selected.mode_octal) {
        setSelected(fresh);
      }
    }
  }, [listing.data, selected]);

  const onCellClick = (entry: FsEntry) => {
    if (entry.is_dir) {
      const next = joinPath(path, entry.name);
      setPath(next);
      setSelected(null);
      return;
    }
    setSelected(entry);
  };

  const onUp = () => {
    setPath(parentOf(path));
    setSelected(null);
  };

  const setBitsAndOctal = (next: PermBits) => {
    setBits(next);
    setOctal(bitsToOctal(next));
  };

  const onOctalChange = (val: string) => {
    setOctal(val);
    if (/^[0-7]{3,4}$/.test(val)) {
      setBits(octalToBits(val));
    }
  };

  const targetPath = useMemo(() => {
    if (!selected) return null;
    return joinPath(path, selected.name);
  }, [path, selected]);

  const onChmodSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!targetPath) return;
    if (!/^[0-7]{3,4}$/.test(octal)) {
      toast.error("Octal mode must be 3 or 4 digits 0-7.");
      return;
    }
    setChmodConfirmOpen(true);
  };

  const onChmodConfirm = async () => {
    if (!targetPath) return;
    try {
      await chmod.mutateAsync({ path: targetPath, mode_octal: octal });
      setChmodConfirmOpen(false);
      toast.success(`chmod ${octal} ${targetPath}`);
    } catch (e) {
      toast.error("chmod failed.", { description: describeError(e) });
    }
  };

  const onChownSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!targetPath) return;
    if (!owner.trim() && !group.trim()) {
      toast.error("Provide owner, group, or both.");
      return;
    }
    setChownConfirmOpen(true);
  };

  const onChownConfirm = async () => {
    if (!targetPath) return;
    try {
      await chown.mutateAsync({
        path: targetPath,
        owner: owner.trim() || null,
        group: group.trim() || null,
      });
      setChownConfirmOpen(false);
      toast.success(`chown ${owner || ""}${group ? ":" + group : ""} ${targetPath}`);
    } catch (e) {
      toast.error("chown failed.", { description: describeError(e) });
    }
  };

  const roots = listing.data?.roots ?? [];

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>File permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {roots.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Quick:</span>
              {roots.map((r) => (
                <Button
                  key={r}
                  variant="outline"
                  size="sm"
                  className="h-7 px-2 font-mono text-[11px]"
                  onClick={() => {
                    setPath(r);
                    setSelected(null);
                  }}
                >
                  {r}
                </Button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={onUp}
              disabled={path === ROOT_PATH}
              className="gap-1.5"
            >
              <ArrowUp className="size-3.5" />
              Up
            </Button>
            <div className="flex items-center gap-1 text-sm flex-wrap">
              {breadcrumbs(path).map((bc, i, arr) => {
                const isLast = i === arr.length - 1;
                return (
                  <span key={bc.full} className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setPath(bc.full);
                        setSelected(null);
                      }}
                      className={cn(
                        "font-mono text-xs",
                        isLast
                          ? "text-foreground"
                          : "text-muted-foreground hover:text-foreground hover:underline",
                      )}
                    >
                      {bc.label}
                    </button>
                    {!isLast && i > 0 && (
                      <span className="text-muted-foreground text-xs">/</span>
                    )}
                  </span>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="font-mono text-sm">{path}</CardTitle>
            {listing.data && (
              <span className="text-xs text-muted-foreground">
                {listing.data.entries.length}
                {listing.data.truncated ? ` (of ${listing.data.total})` : ""} entries
              </span>
            )}
          </CardHeader>
          <CardContent>
            {listing.isLoading && !listing.data ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-7" />
                ))}
              </div>
            ) : listing.error ? (
              <div className="py-6 text-center text-sm text-destructive">
                Failed to load. {describeError(listing.error)}
              </div>
            ) : listing.data && listing.data.entries.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Empty directory.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-muted-foreground border-b border-border">
                      <th className="py-2 px-2 font-medium">Name</th>
                      <th className="py-2 px-2 font-medium">Mode</th>
                      <th className="py-2 px-2 font-medium">Owner</th>
                      <th className="py-2 px-2 font-medium">Group</th>
                      <th className="py-2 px-2 font-medium text-right">Size</th>
                      <th className="py-2 px-2 font-medium">Modified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(listing.data?.entries ?? []).map((e) => {
                      const isSelected =
                        selected?.name === e.name && !e.is_dir;
                      return (
                        <tr
                          key={e.name}
                          onClick={() => onCellClick(e)}
                          className={cn(
                            "border-b border-border/60 last:border-b-0 cursor-pointer transition-colors",
                            isSelected
                              ? "bg-accent/60"
                              : "hover:bg-accent/40",
                          )}
                        >
                          <td className="py-1.5 px-2">
                            <span className="flex items-center gap-1.5 min-w-0">
                              {e.is_link ? (
                                <LinkIcon className="size-3.5 shrink-0 text-muted-foreground" />
                              ) : e.is_dir ? (
                                <FolderOpen className="size-3.5 shrink-0 text-amber-500" />
                              ) : (
                                <FileIcon className="size-3.5 shrink-0 text-muted-foreground" />
                              )}
                              <span className="truncate font-mono text-xs">
                                {e.name}
                                {e.is_dir ? "/" : ""}
                              </span>
                            </span>
                          </td>
                          <td className="py-1.5 px-2 font-mono text-xs">
                            {e.mode_octal}
                          </td>
                          <td className="py-1.5 px-2 font-mono text-xs">
                            {e.owner}
                          </td>
                          <td className="py-1.5 px-2 font-mono text-xs">
                            {e.group}
                          </td>
                          <td className="py-1.5 px-2 font-mono text-xs text-right">
                            {e.is_dir ? "-" : formatBytes(e.size)}
                          </td>
                          <td className="py-1.5 px-2 text-xs text-muted-foreground whitespace-nowrap">
                            {formatTs(e.mtime)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Action panel</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selected ? (
              <div className="text-sm text-muted-foreground">
                Click a file in the list to chmod or chown it.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-md border border-border bg-muted/40 px-3 py-2 space-y-1 text-xs">
                  <div className="font-mono break-all">{targetPath}</div>
                  <div className="text-muted-foreground">
                    {selected.owner}:{selected.group} mode {selected.mode_octal}
                  </div>
                </div>

                <form onSubmit={onChmodSubmit} className="space-y-3">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                      chmod
                    </Label>
                    <PermGrid bits={bits} onChange={setBitsAndOctal} />
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="space-y-1.5 flex-1">
                      <Label htmlFor="octal">Octal</Label>
                      <Input
                        id="octal"
                        value={octal}
                        onChange={(e) => onOctalChange(e.target.value)}
                        className="font-mono"
                        placeholder="644"
                      />
                    </div>
                    <Button
                      type="submit"
                      size="sm"
                      disabled={chmod.isPending}
                    >
                      Apply chmod
                    </Button>
                  </div>
                </form>

                <form onSubmit={onChownSubmit} className="space-y-3">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                      chown
                    </Label>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1.5">
                        <Label htmlFor="owner">Owner</Label>
                        <Input
                          id="owner"
                          value={owner}
                          onChange={(e) => setOwner(e.target.value)}
                          className="font-mono"
                          placeholder="root"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="group">Group</Label>
                        <Input
                          id="group"
                          value={group}
                          onChange={(e) => setGroup(e.target.value)}
                          className="font-mono"
                          placeholder="root"
                        />
                      </div>
                    </div>
                  </div>
                  <Button type="submit" size="sm" disabled={chown.isPending}>
                    Apply chown
                  </Button>
                </form>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={chmodConfirmOpen}
        onOpenChange={setChmodConfirmOpen}
        title="Confirm chmod"
        description={
          targetPath ? (
            <>
              Set mode <span className="font-mono">{octal}</span> on
              <span className="font-mono break-all"> {targetPath}</span>?
            </>
          ) : null
        }
        onConfirm={onChmodConfirm}
        pending={chmod.isPending}
      />

      <ConfirmDialog
        open={chownConfirmOpen}
        onOpenChange={setChownConfirmOpen}
        title="Confirm chown"
        description={
          targetPath ? (
            <>
              Change ownership to{" "}
              <span className="font-mono">
                {owner || "(unchanged)"}
                {group ? ":" + group : ""}
              </span>{" "}
              on <span className="font-mono break-all">{targetPath}</span>?
            </>
          ) : null
        }
        onConfirm={onChownConfirm}
        pending={chown.isPending}
      />
    </div>
  );
}

type PermGridProps = {
  bits: PermBits;
  onChange: (b: PermBits) => void;
};

function PermGrid({ bits, onChange }: PermGridProps) {
  const setBit = (key: keyof PermBits, val: boolean) =>
    onChange({ ...bits, [key]: val });

  const Row = (
    title: string,
    keys: [keyof PermBits, keyof PermBits, keyof PermBits],
  ) => (
    <tr>
      <td className="py-1 px-2 text-xs text-muted-foreground">{title}</td>
      {(["r", "w", "x"] as const).map((label, i) => {
        const key = keys[i];
        return (
          <td key={label} className="py-1 px-2">
            <label className="flex items-center gap-1.5 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={bits[key]}
                onChange={(e) => setBit(key, e.target.checked)}
                className="size-3.5"
              />
              <span className="font-mono">{label}</span>
            </label>
          </td>
        );
      })}
    </tr>
  );

  return (
    <table className="border border-border rounded-md text-sm">
      <thead>
        <tr className="text-xs text-muted-foreground">
          <th className="py-1 px-2 text-left font-medium">who</th>
          <th className="py-1 px-2 text-left font-medium">read</th>
          <th className="py-1 px-2 text-left font-medium">write</th>
          <th className="py-1 px-2 text-left font-medium">exec</th>
        </tr>
      </thead>
      <tbody>
        {Row("user", ["ur", "uw", "ux"])}
        {Row("group", ["gr", "gw", "gx"])}
        {Row("other", ["or", "ow", "ox"])}
      </tbody>
    </table>
  );
}

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  title: string;
  description: React.ReactNode;
  onConfirm: () => void;
  pending: boolean;
};

function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  pending,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription asChild>
            <div className="text-sm text-muted-foreground">{description}</div>
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
          <Button onClick={onConfirm} disabled={pending}>
            {pending ? "Applying..." : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

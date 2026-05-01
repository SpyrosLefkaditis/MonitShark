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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { FirewallRuleInput } from "@/types";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: FirewallRuleInput) => void;
  pending?: boolean;
};

const PORT_PATTERN = /^([1-9][0-9]{0,4}|[a-zA-Z][a-zA-Z0-9_.-]*)$/;
const SOURCE_PATTERN = /^(any|[0-9a-fA-F:./]+)$/;

export function AddRuleDialog({ open, onOpenChange, onSubmit, pending }: Props) {
  const [action, setAction] = useState<FirewallRuleInput["action"]>("allow");
  const [port, setPort] = useState("");
  const [proto, setProto] = useState<"any" | "tcp" | "udp">("any");
  const [source, setSource] = useState("any");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setAction("allow");
      setPort("");
      setProto("any");
      setSource("any");
      setComment("");
      setError(null);
    }
  }, [open]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const portTrim = port.trim();
    if (!PORT_PATTERN.test(portTrim)) {
      setError("Port must be 1-65535 or a service name (e.g. ssh).");
      return;
    }
    const portNum = /^\d+$/.test(portTrim) ? Number(portTrim) : portTrim;
    if (typeof portNum === "number" && (portNum < 1 || portNum > 65535)) {
      setError("Port out of range (1-65535).");
      return;
    }
    const srcTrim = source.trim() || "any";
    if (!SOURCE_PATTERN.test(srcTrim)) {
      setError("Source must be 'any' or a CIDR/IP.");
      return;
    }
    setError(null);
    onSubmit({
      action,
      port: portNum,
      proto: proto === "any" ? null : proto,
      source: srcTrim === "any" ? null : srcTrim,
      comment: comment.trim() || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New firewall rule</DialogTitle>
          <DialogDescription>
            Append a UFW rule. Use a numeric port or a service name; leave source as <span className="font-mono">any</span> to apply to all sources.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="fw-action">Action</Label>
              <Select value={action} onValueChange={(v) => setAction(v as FirewallRuleInput["action"])}>
                <SelectTrigger id="fw-action">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="allow">allow</SelectItem>
                  <SelectItem value="deny">deny</SelectItem>
                  <SelectItem value="reject">reject</SelectItem>
                  <SelectItem value="limit">limit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="fw-port">Port / service</Label>
              <Input
                id="fw-port"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="22 or ssh"
                className="font-mono"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="fw-proto">Protocol</Label>
              <Select value={proto} onValueChange={(v) => setProto(v as "any" | "tcp" | "udp")}>
                <SelectTrigger id="fw-proto">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">any</SelectItem>
                  <SelectItem value="tcp">tcp</SelectItem>
                  <SelectItem value="udp">udp</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="fw-source">Source</Label>
              <Input
                id="fw-source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="any or CIDR"
                className="font-mono"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="fw-comment">Comment (optional)</Label>
            <Input
              id="fw-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Allow internal SSH"
              maxLength={120}
            />
          </div>
          {error && <p className="text-[12px] text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Adding…" : "Add rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

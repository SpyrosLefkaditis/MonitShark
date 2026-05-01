import { Pencil, Play, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { CronEntry } from "@/types";

type Props = {
  entries: CronEntry[];
  onRun: (e: CronEntry) => void;
  onEdit: (e: CronEntry) => void;
  onDelete: (e: CronEntry) => void;
};

export function CronTable({ entries, onRun, onEdit, onDelete }: Props) {
  if (entries.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        No cron entries yet. Click “New cron job” to add one.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-2 px-3 font-medium">User</th>
            <th className="py-2 px-3 font-medium">Schedule</th>
            <th className="py-2 px-3 font-medium">Command</th>
            <th className="py-2 px-3 font-medium">Comment</th>
            <th className="py-2 px-3 font-medium">Status</th>
            <th className="py-2 px-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id} className="border-b border-border/60 last:border-b-0 hover:bg-accent/40">
              <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{e.user}</td>
              <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{e.schedule}</td>
              <td className="py-2 px-3 font-mono text-xs max-w-[28rem] truncate" title={e.command}>
                {e.command}
              </td>
              <td className="py-2 px-3 text-xs text-muted-foreground max-w-[14rem] truncate">
                {e.comment ?? "—"}
              </td>
              <td className="py-2 px-3">
                <Badge variant={e.enabled ? "success" : "outline"} className="text-[10px]">
                  {e.enabled ? "enabled" : "disabled"}
                </Badge>
              </td>
              <td className="py-2 px-3">
                <div className="flex items-center justify-end gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="size-7"
                        onClick={() => onRun(e)}
                        aria-label="Run now"
                      >
                        <Play className="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Run now</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="size-7"
                        onClick={() => onEdit(e)}
                        aria-label="Edit"
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Edit</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="size-7"
                        onClick={() => onDelete(e)}
                        aria-label="Delete"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Delete</TooltipContent>
                  </Tooltip>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

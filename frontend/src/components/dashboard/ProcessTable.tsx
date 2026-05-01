import { formatBytes, formatPercent } from "@/lib/format";
import type { ProcessItem } from "@/types";

type Props = {
  processes: ProcessItem[];
  limit?: number;
};

export function ProcessTable({ processes, limit = 10 }: Props) {
  const rows = processes.slice(0, limit);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-2 pr-3 font-medium">PID</th>
            <th className="py-2 pr-3 font-medium">Name</th>
            <th className="py-2 pr-3 font-medium">User</th>
            <th className="py-2 pr-3 font-medium text-right">CPU</th>
            <th className="py-2 pr-3 font-medium text-right">Mem</th>
            <th className="py-2 pr-0 font-medium text-right">RSS</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="py-6 text-center text-xs text-muted-foreground">
                No process data.
              </td>
            </tr>
          )}
          {rows.map((p) => (
            <tr
              key={p.pid}
              className="border-b border-border/60 last:border-b-0 hover:bg-accent/40"
            >
              <td className="py-1.5 pr-3 font-mono tabular-nums text-xs">{p.pid}</td>
              <td className="py-1.5 pr-3 truncate max-w-[160px]" title={p.cmdline || p.name}>
                {p.name}
              </td>
              <td className="py-1.5 pr-3 text-muted-foreground text-xs truncate max-w-[80px]">
                {p.user ?? "—"}
              </td>
              <td className="py-1.5 pr-3 font-mono tabular-nums text-right text-xs">
                {formatPercent(p.cpu_percent)}
              </td>
              <td className="py-1.5 pr-3 font-mono tabular-nums text-right text-xs">
                {formatPercent(p.mem_percent)}
              </td>
              <td className="py-1.5 pr-0 font-mono tabular-nums text-right text-xs">
                {formatBytes(p.rss)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

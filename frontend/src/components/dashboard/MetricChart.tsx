import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MetricsSnapshot } from "@/types";

type Props = {
  buffer: MetricsSnapshot[];
  height?: number;
};

function rootDiskPct(snap: MetricsSnapshot): number {
  const root = snap.disks.find((d) => d.mountpoint === "/") ?? snap.disks[0];
  return root ? root.percent : 0;
}

export function MetricChart({ buffer, height = 260 }: Props) {
  if (buffer.length === 0) {
    return (
      <div
        style={{ height }}
        className="grid place-items-center text-sm text-muted-foreground"
      >
        Waiting for first metrics frame…
      </div>
    );
  }
  const lastTs = buffer[buffer.length - 1].ts;
  const data = buffer.map((s) => ({
    t: Math.round(s.ts - lastTs),
    cpu: Math.round(s.cpu.percent * 10) / 10,
    mem: Math.round(s.memory.percent * 10) / 10,
    disk: Math.round(rootDiskPct(s) * 10) / 10,
  }));
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="t"
            tickFormatter={(v) => `${v}s`}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            width={36}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={(v) => `t=${v}s`}
            formatter={(v: number, name) => [`${v}%`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="cpu"
            name="CPU"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="mem"
            name="Memory"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="disk"
            name="Disk /"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

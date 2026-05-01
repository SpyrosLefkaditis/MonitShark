import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";

type Props = {
  data: number[];
  color?: string;
  domain?: [number | "auto", number | "auto"];
  height?: number;
};

export function Sparkline({
  data,
  color = "hsl(var(--primary))",
  domain = ["auto", "auto"],
  height = 40,
}: Props) {
  if (!data.length) {
    return <div style={{ height }} className="w-full" aria-hidden />;
  }
  const series = data.map((v, i) => ({ i, v }));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <YAxis hide domain={domain} />
          <Line
            dataKey="v"
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

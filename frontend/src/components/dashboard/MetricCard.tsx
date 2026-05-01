import { ArrowDown, ArrowRight, ArrowUp, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import { Sparkline } from "./Sparkline";

type Props = {
  title: string;
  value: string;
  subtitle?: string;
  series: number[];
  icon?: LucideIcon;
  /** Optional explicit delta. If absent, computed from series[0..30] vs latest. */
  delta?: number;
  /** Lower-is-better (e.g. CPU%). Affects arrow color tone. */
  lowerIsBetter?: boolean;
  /** Sparkline color (Tailwind/HSL). */
  color?: string;
  /** Sparkline domain. Defaults to auto. */
  domain?: [number | "auto", number | "auto"];
};

function computeDelta(series: number[]): number | null {
  if (series.length < 2) return null;
  const latest = series[series.length - 1];
  const ref = series[Math.max(0, series.length - 31)] ?? series[0];
  return latest - ref;
}

export function MetricCard({
  title,
  value,
  subtitle,
  series,
  icon: Icon,
  delta,
  lowerIsBetter,
  color,
  domain,
}: Props) {
  const d = delta ?? computeDelta(series);
  const ArrowIcon = d == null ? ArrowRight : d > 0.1 ? ArrowUp : d < -0.1 ? ArrowDown : ArrowRight;
  const trendUp = d != null && d > 0.1;
  const trendDown = d != null && d < -0.1;
  const trendBad = (lowerIsBetter && trendUp) || (!lowerIsBetter && trendDown);
  const trendGood = (lowerIsBetter && trendDown) || (!lowerIsBetter && trendUp);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {Icon && <Icon className="size-3.5" />}
              <span>{title}</span>
            </div>
            <div className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">
              {value}
            </div>
            {(subtitle || d != null) && (
              <div className="mt-0.5 flex items-center gap-1 text-[11px]">
                {d != null && (
                  <span
                    className={cn(
                      "inline-flex items-center gap-0.5 font-mono",
                      trendBad && "text-destructive",
                      trendGood && "text-emerald-500",
                      !trendBad && !trendGood && "text-muted-foreground",
                    )}
                  >
                    <ArrowIcon className="size-3" />
                    {d.toFixed(1)}
                  </span>
                )}
                {subtitle && <span className="text-muted-foreground">{subtitle}</span>}
              </div>
            )}
          </div>
          <div className="w-24 shrink-0">
            <Sparkline data={series} color={color} domain={domain} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

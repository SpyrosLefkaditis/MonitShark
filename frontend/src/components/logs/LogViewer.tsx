import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type Props = {
  lines: string[];
  /** Scroll to bottom when `lines` changes (i.e. on refresh). */
  autoscroll?: boolean;
  className?: string;
};

export function LogViewer({ lines, autoscroll = true, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoscroll) return;
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines, autoscroll]);

  return (
    <div
      ref={ref}
      className={cn(
        "rounded-md border border-border bg-[#0b0d10] text-zinc-200 font-mono text-[12px] leading-snug overflow-auto",
        "max-h-[60vh]",
        className,
      )}
    >
      {lines.length === 0 ? (
        <div className="p-4 text-zinc-500">No log lines.</div>
      ) : (
        <pre className="p-3">
          {lines.map((l, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-zinc-600 select-none w-10 text-right shrink-0">{i + 1}</span>
              <span className="whitespace-pre-wrap break-all">{l}</span>
            </div>
          ))}
        </pre>
      )}
    </div>
  );
}

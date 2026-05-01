import { useCallback, useMemo, useRef, useState } from "react";

import { wsUrl } from "@/lib/api";
import type { DockerLogFrame } from "@/types";

import { useWebSocket } from "./useWebSocket";

const MAX_LINES = 2000;

type LogEntry = {
  id: number;
  line: string;
  ts: number;
};

export type UseDockerLogsResult = {
  lines: LogEntry[];
  paused: boolean;
  togglePause: () => void;
  clear: () => void;
  readyState: number;
  error: string | null;
};

/**
 * Subscribe to /ws/docker/logs/{id} and accumulate decoded log lines into a
 * bounded buffer. While paused, incoming frames are dropped on the floor —
 * we deliberately do NOT buffer paused frames to avoid runaway memory.
 */
export function useDockerLogs(
  containerId: string | null,
  options?: { tail?: number; follow?: boolean; enabled?: boolean },
): UseDockerLogsResult {
  const { tail = 200, follow = true, enabled = true } = options ?? {};

  const url = useMemo(() => {
    if (!containerId || !enabled) return null;
    const path = `/ws/docker/logs/${encodeURIComponent(containerId)}?tail=${tail}&follow=${follow}`;
    return wsUrl(path);
  }, [containerId, tail, follow, enabled]);

  const [lines, setLines] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(0);
  const pausedRef = useRef(false);
  pausedRef.current = paused;

  const handleMessage = useCallback((data: unknown) => {
    if (!data || typeof data !== "object") return;
    const frame = data as DockerLogFrame;
    if (frame.type === "error") {
      setError(frame.message ?? "log stream error");
      return;
    }
    if (frame.type !== "log") return;
    if (pausedRef.current) return;
    setLines((prev) => {
      const id = ++idRef.current;
      const entry: LogEntry = { id, line: frame.line, ts: frame.ts };
      const next = prev.length >= MAX_LINES ? prev.slice(prev.length - (MAX_LINES - 1)) : prev.slice();
      next.push(entry);
      return next;
    });
  }, []);

  const handleOpen = useCallback(() => setError(null), []);

  const { readyState } = useWebSocket(url, {
    onMessage: handleMessage,
    onOpen: handleOpen,
    enabled: !!url,
  });

  const togglePause = useCallback(() => setPaused((p) => !p), []);

  const clear = useCallback(() => {
    setLines([]);
    idRef.current = 0;
  }, []);

  return { lines, paused, togglePause, clear, readyState, error };
}

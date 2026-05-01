import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { wsUrl } from "@/lib/api";
import type { MetricsSnapshot } from "@/types";

import { useMetrics } from "./useMetrics";
import { useWebSocket } from "./useWebSocket";

const RING_SIZE = 60;

/**
 * Live metrics over WebSocket with REST fallback.
 * - Maintains a 60-frame ring buffer of MetricsSnapshot.
 * - Falls back to single-snapshot REST polling when the WS isn't open.
 */
export function useLiveMetrics() {
  const url = useMemo(() => wsUrl("/ws/metrics"), []);
  const [buffer, setBuffer] = useState<MetricsSnapshot[]>([]);
  const restQuery = useMetrics();
  const lastRestTsRef = useRef<number | null>(null);

  const handleMessage = useCallback((data: unknown) => {
    if (!data || typeof data !== "object") return;
    const snap = data as MetricsSnapshot;
    if (typeof snap.ts !== "number" || !snap.cpu || !snap.memory) return;
    setBuffer((prev) => {
      const next = prev.length >= RING_SIZE ? prev.slice(prev.length - (RING_SIZE - 1)) : prev.slice();
      next.push(snap);
      return next;
    });
  }, []);

  const { readyState } = useWebSocket(url, { onMessage: handleMessage });

  // REST fallback while WS isn't open: append latest unique snapshot to buffer so the UI still progresses.
  useEffect(() => {
    if (readyState === WebSocket.OPEN) return;
    const snap = restQuery.data;
    if (!snap) return;
    if (lastRestTsRef.current === snap.ts) return;
    lastRestTsRef.current = snap.ts;
    setBuffer((prev) => {
      const next = prev.length >= RING_SIZE ? prev.slice(prev.length - (RING_SIZE - 1)) : prev.slice();
      next.push(snap);
      return next;
    });
  }, [readyState, restQuery.data]);

  const latest = buffer.length > 0 ? buffer[buffer.length - 1] : restQuery.data ?? null;

  return {
    buffer,
    latest,
    readyState,
    isLoading: buffer.length === 0 && restQuery.isLoading,
    error: restQuery.error,
  };
}

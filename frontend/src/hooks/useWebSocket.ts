import { useCallback, useEffect, useRef, useState } from "react";

export type WSMessage = unknown;

export type WSReadyState =
  | typeof WebSocket.CONNECTING
  | typeof WebSocket.OPEN
  | typeof WebSocket.CLOSING
  | typeof WebSocket.CLOSED;

export type UseWebSocketOptions = {
  enabled?: boolean;
  onOpen?: (ev: Event) => void;
  onClose?: (ev: CloseEvent) => void;
  onError?: (ev: Event) => void;
  onMessage?: (data: WSMessage) => void;
};

export type UseWebSocketResult = {
  readyState: WSReadyState;
  send: (data: unknown) => boolean;
  lastMessage: WSMessage | null;
};

/**
 * Generic WebSocket hook with automatic exponential-backoff reconnect.
 * - Parses each frame as JSON; falls back to raw text on parse failure.
 * - Backoff sequence: 1s, 2s, 4s, 8s, capped at 10s.
 * - Caller MUST memoize `url` and `opts` (or pass an inline string + stable callbacks via refs).
 */
export function useWebSocket(
  url: string | null,
  opts: UseWebSocketOptions = {},
): UseWebSocketResult {
  const { enabled = true, onOpen, onClose, onError, onMessage } = opts;

  // Stash callbacks in refs so reconnects don't fire on every render-time identity change.
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);
  const onMessageRef = useRef(onMessage);
  useEffect(() => {
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
    onMessageRef.current = onMessage;
  }, [onOpen, onClose, onError, onMessage]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const closedByCallerRef = useRef(false);
  const [readyState, setReadyState] = useState<WSReadyState>(WebSocket.CLOSED);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  useEffect(() => {
    if (!enabled || !url) {
      return;
    }
    closedByCallerRef.current = false;

    const connect = () => {
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("WebSocket constructor failed:", err);
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;
      setReadyState(WebSocket.CONNECTING);

      ws.onopen = (ev) => {
        reconnectAttemptsRef.current = 0;
        setReadyState(WebSocket.OPEN);
        onOpenRef.current?.(ev);
      };
      ws.onclose = (ev) => {
        setReadyState(WebSocket.CLOSED);
        onCloseRef.current?.(ev);
        if (!closedByCallerRef.current) {
          scheduleReconnect();
        }
      };
      ws.onerror = (ev) => {
        onErrorRef.current?.(ev);
      };
      ws.onmessage = (ev) => {
        let data: WSMessage = ev.data;
        if (typeof ev.data === "string") {
          try {
            data = JSON.parse(ev.data);
          } catch {
            data = ev.data;
          }
        }
        setLastMessage(data);
        onMessageRef.current?.(data);
      };
    };

    const scheduleReconnect = () => {
      const attempt = reconnectAttemptsRef.current;
      const delay = Math.min(1000 * Math.pow(2, attempt), 10_000);
      reconnectAttemptsRef.current = attempt + 1;
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    };

    connect();

    return () => {
      closedByCallerRef.current = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        ws.onopen = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          try {
            ws.close();
          } catch {
            /* noop */
          }
        }
      }
      setReadyState(WebSocket.CLOSED);
    };
  }, [url, enabled]);

  const send = useCallback((data: unknown): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const payload = typeof data === "string" ? data : JSON.stringify(data);
    ws.send(payload);
    return true;
  }, []);

  return { readyState, send, lastMessage };
}

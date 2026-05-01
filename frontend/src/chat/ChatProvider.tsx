import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";

import { useWebSocket } from "@/hooks/useWebSocket";
import { wsUrl } from "@/lib/api";

import { chatReducer } from "./reducer";
import { type ChatState, type ServerFrame, initialChatState } from "./types";

type Ctx = {
  state: ChatState;
  threadId: string;
  drawerOpen: boolean;
  connected: boolean;
  draft: string;
  setDraft: (text: string) => void;
  sendMessage: (text: string) => void;
  respondConfirmation: (request_id: string, decision: "approve" | "deny") => void;
  prefill: (text: string) => void;
  clear: () => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
};

const ChatContext = createContext<Ctx | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const threadId = useMemo(() => `thread-${Date.now()}`, []);
  const url = useMemo(() => wsUrl(`/ws/chat?thread_id=${encodeURIComponent(threadId)}`), [threadId]);

  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draft, setDraft] = useState("");

  const handleMessage = useCallback((data: unknown) => {
    if (!data || typeof data !== "object" || !("type" in (data as object))) return;
    const frame = data as ServerFrame;
    dispatch({ type: "server_frame", frame });
    if (frame.type === "error") {
      toast.error(frame.message);
    }
  }, []);

  const { readyState, send } = useWebSocket(url, { onMessage: handleMessage });
  const connected = readyState === WebSocket.OPEN;

  // Track sends so users get feedback if the socket isn't open yet.
  const pendingWarnRef = useRef<number>(0);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      dispatch({ type: "send_user", text: trimmed });
      const ok = send({ type: "user", text: trimmed });
      if (!ok) {
        const now = Date.now();
        if (now - pendingWarnRef.current > 4000) {
          pendingWarnRef.current = now;
          toast.error("Chat not connected. Reconnecting…");
        }
      }
    },
    [send],
  );

  const respondConfirmation = useCallback(
    (request_id: string, decision: "approve" | "deny") => {
      dispatch({ type: "resolve_confirmation", request_id, decision });
      send({ type: "confirm", request_id, decision });
    },
    [send],
  );

  const prefill = useCallback((text: string) => {
    setDraft(text);
  }, []);

  const clear = useCallback(() => {
    dispatch({ type: "clear" });
  }, []);

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const toggleDrawer = useCallback(() => setDrawerOpen((v) => !v), []);

  const value: Ctx = {
    state,
    threadId,
    drawerOpen,
    connected,
    draft,
    setDraft,
    sendMessage,
    respondConfirmation,
    prefill,
    clear,
    openDrawer,
    closeDrawer,
    toggleDrawer,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): Ctx {
  const c = useContext(ChatContext);
  if (!c) throw new Error("useChat must be used inside <ChatProvider>");
  return c;
}

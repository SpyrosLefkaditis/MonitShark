import { Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";

import { useChat } from "@/chat/ChatProvider";
import type { ChatMessage } from "@/chat/types";
import { cn } from "@/lib/utils";

import { ConfirmationCard } from "./ConfirmationCard";
import { MessageBubble } from "./MessageBubble";
import { ToolCallCard } from "./ToolCallCard";

function renderMessage(
  m: ChatMessage,
  onDecide: (request_id: string, decision: "approve" | "deny") => void,
) {
  switch (m.kind) {
    case "user":
      return <MessageBubble key={m.id} role="user" text={m.text} />;
    case "assistant":
      return <MessageBubble key={m.id} role="assistant" text={m.text} streaming={m.streaming} />;
    case "tool_call":
      return (
        <ToolCallCard
          key={m.id}
          name={m.name}
          args={m.args}
          status={m.status}
          ok={m.ok}
          output={m.output}
        />
      );
    case "confirmation":
      return (
        <ConfirmationCard
          key={m.id}
          action={m.action}
          args={m.args}
          summary={m.summary}
          risk={m.risk}
          decision={m.decision}
          onDecide={(d) => onDecide(m.request_id, d)}
        />
      );
    case "error":
      return (
        <div
          key={m.id}
          className={cn(
            "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive",
          )}
        >
          {m.text}
        </div>
      );
  }
}

export function MessageList() {
  const { state, respondConfirmation } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on any state change.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [state.messages]);

  if (state.messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 gap-3">
        <div className="size-10 rounded-md bg-primary/15 grid place-items-center text-primary">
          <Sparkles className="size-5" />
        </div>
        <div>
          <p className="text-sm font-medium">Ask Beacon anything about this host.</p>
          <p className="text-xs text-muted-foreground mt-1">
            Try “summarize active alerts”, “tail /var/log/auth.log”, or “run a security audit”.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {state.messages.map((m) => renderMessage(m, respondConfirmation))}
    </div>
  );
}

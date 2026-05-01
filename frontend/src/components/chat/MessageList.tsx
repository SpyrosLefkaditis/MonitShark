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

// Lightweight content signature so the autoscroll effect re-fires whenever an
// existing message GROWS (streaming tokens) or a tool_call's status flips —
// not only when the array length changes. Without this the streaming
// assistant bubble appends below the fold and the user can't see it without
// closing+reopening the drawer.
function contentSignature(state: { messages: ChatMessage[] }): string {
  const out: string[] = [`n=${state.messages.length}`];
  for (const m of state.messages) {
    switch (m.kind) {
      case "assistant":
        out.push(`a:${m.id}:${m.text.length}:${m.streaming ? "s" : "f"}`);
        break;
      case "tool_call": {
        const outLen = typeof m.output === "string" ? m.output.length : m.output ? 1 : 0;
        out.push(`t:${m.id}:${m.status}:${outLen}`);
        break;
      }
      case "user":
        out.push(`u:${m.id}`);
        break;
      case "confirmation":
        out.push(`c:${m.id}:${m.decision ?? "pending"}`);
        break;
      case "error":
        out.push(`e:${m.id}`);
        break;
    }
  }
  return out.join("|");
}

export function MessageList() {
  const { state, respondConfirmation } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sig = contentSignature(state);

  useEffect(() => {
    // requestAnimationFrame so layout has reflowed before we measure.
    const id = requestAnimationFrame(() => {
      const sentinel = bottomRef.current;
      if (sentinel && typeof sentinel.scrollIntoView === "function") {
        sentinel.scrollIntoView({ block: "end", behavior: "auto" });
        return;
      }
      const c = scrollRef.current;
      if (c) c.scrollTop = c.scrollHeight;
    });
    return () => cancelAnimationFrame(id);
  }, [sig]);

  if (state.messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 gap-3">
        <div className="size-10 rounded-md bg-primary/15 grid place-items-center text-primary">
          <Sparkles className="size-5" />
        </div>
        <div>
          <p className="text-sm font-medium">Ask MonitShark anything about this host.</p>
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
      <div ref={bottomRef} aria-hidden className="h-px shrink-0" />
    </div>
  );
}

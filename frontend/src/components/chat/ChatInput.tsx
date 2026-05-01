import { Send } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef } from "react";

import { useChat } from "@/chat/ChatProvider";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export function ChatInput() {
  const { draft, setDraft, sendMessage, state, connected } = useChat();
  const ref = useRef<HTMLTextAreaElement>(null);

  // Re-focus textarea after the drawer mounts.
  useEffect(() => {
    ref.current?.focus();
  }, []);

  const disabled = state.awaitingConfirmation;

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && draft.trim()) {
        sendMessage(draft);
        setDraft("");
      }
    }
  };

  const onSend = () => {
    if (disabled || !draft.trim()) return;
    sendMessage(draft);
    setDraft("");
  };

  return (
    <div className="border-t border-border bg-card p-3">
      <div className="flex items-end gap-2">
        <Textarea
          ref={ref}
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            disabled
              ? "Resolve the confirmation above to continue…"
              : connected
                ? "Message Beacon (Enter to send, Shift+Enter for newline)"
                : "Connecting…"
          }
          disabled={disabled}
          className={cn("resize-none min-h-[60px] max-h-40")}
        />
        <Button
          size="icon"
          onClick={onSend}
          disabled={disabled || !draft.trim()}
          aria-label="Send"
          title="Send"
        >
          <Send className="size-4" />
        </Button>
      </div>
      <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>
          {connected ? (
            <span className="text-emerald-500">● connected</span>
          ) : (
            <span className="text-amber-500">○ reconnecting…</span>
          )}
        </span>
        <span className="font-mono">Enter ↵ send · Shift+Enter newline</span>
      </div>
    </div>
  );
}

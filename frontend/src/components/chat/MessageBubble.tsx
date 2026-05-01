import { Bot, User } from "lucide-react";

import { cn } from "@/lib/utils";

import { MarkdownRenderer } from "./MarkdownRenderer";

type Props = {
  role: "user" | "assistant";
  text: string;
  streaming?: boolean;
};

export function MessageBubble({ role, text, streaming }: Props) {
  const isUser = role === "user";
  return (
    <div className={cn("flex gap-2", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="size-7 mt-0.5 rounded-md bg-primary/15 grid place-items-center text-primary shrink-0">
          <Bot className="size-3.5" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm break-words",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-card border border-border rounded-tl-sm",
        )}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{text}</div>
        ) : (
          <>
            <MarkdownRenderer source={text || (streaming ? "…" : "")} />
            {streaming && (
              <span
                aria-hidden
                className="ml-1 inline-block size-1.5 align-baseline rounded-full bg-foreground/60 animate-pulse"
              />
            )}
          </>
        )}
      </div>
      {isUser && (
        <div className="size-7 mt-0.5 rounded-md bg-secondary grid place-items-center text-foreground shrink-0">
          <User className="size-3.5" />
        </div>
      )}
    </div>
  );
}

import { Eraser } from "lucide-react";

import { useChat } from "@/chat/ChatProvider";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";

import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

export function ChatDrawer() {
  const { drawerOpen, closeDrawer, clear, state } = useChat();
  const onOpenChange = (open: boolean) => {
    if (!open) closeDrawer();
  };
  return (
    <Sheet open={drawerOpen} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md md:max-w-xl flex flex-col p-0 gap-0"
      >
        <header className="px-4 py-3 border-b border-border flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="size-7 rounded-md bg-primary/15 grid place-items-center text-primary">
              <span className="text-xs font-bold">B</span>
            </div>
            <div>
              <div className="text-sm font-semibold leading-tight">Beacon AI</div>
              <div className="text-[11px] text-muted-foreground leading-tight">
                Conversational system administration
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={clear}
            disabled={state.messages.length === 0}
            className="gap-1.5 mr-8"
          >
            <Eraser className="size-3.5" />
            Clear
          </Button>
        </header>
        <MessageList />
        <ChatInput />
      </SheetContent>
    </Sheet>
  );
}

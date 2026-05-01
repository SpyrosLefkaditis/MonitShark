import { useState } from "react";
import { Outlet } from "react-router-dom";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function RootLayout() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar onChatToggle={() => setChatOpen((v) => !v)} />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <Sheet open={chatOpen} onOpenChange={setChatOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md md:max-w-lg flex flex-col">
          <SheetHeader>
            <SheetTitle>Beacon AI</SheetTitle>
            <SheetDescription>
              Chat with the agent. Wired in Phase 6.
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Chat panel will appear here.
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

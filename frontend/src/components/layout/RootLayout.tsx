import { Outlet } from "react-router-dom";

import { ChatDrawer } from "@/components/chat/ChatDrawer";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function RootLayout() {
  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <ChatDrawer />
    </div>
  );
}

import { LogOut, MessageSquare } from "lucide-react";
import { useLocation } from "react-router-dom";

import { useAuth } from "@/auth/AuthProvider";
import { useChat } from "@/chat/ChatProvider";
import { Button } from "@/components/ui/button";

import { AlertsBadge } from "./AlertsBadge";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/services": "Services",
  "/cron": "Cron",
  "/audit": "Audit",
  "/logs": "Logs",
};

export function Topbar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const { toggleDrawer } = useChat();
  const title = TITLES[pathname] ?? "MonitShark";
  return (
    <header className="h-14 shrink-0 border-b border-border bg-card/60 backdrop-blur flex items-center justify-between px-6">
      <h1 className="text-base font-semibold tracking-tight">{title}</h1>
      <div className="flex items-center gap-3">
        <AlertsBadge />
        <Button variant="outline" size="sm" onClick={toggleDrawer} className="gap-2">
          <MessageSquare className="size-4" />
          <span>Ask MonitShark</span>
        </Button>
        {user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-border">
            <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
              {user.username}
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

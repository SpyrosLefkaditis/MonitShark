import { MessageSquare } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";

import { AlertsBadge } from "./AlertsBadge";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/services": "Services",
  "/cron": "Cron",
  "/audit": "Audit",
  "/logs": "Logs",
};

export function Topbar({ onChatToggle }: { onChatToggle: () => void }) {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "Beacon";
  return (
    <header className="h-14 shrink-0 border-b border-border bg-card/60 backdrop-blur flex items-center justify-between px-6">
      <h1 className="text-base font-semibold tracking-tight">{title}</h1>
      <div className="flex items-center gap-3">
        <AlertsBadge />
        <Button variant="outline" size="sm" onClick={onChatToggle} className="gap-2">
          <MessageSquare className="size-4" />
          <span>Ask Beacon</span>
        </Button>
      </div>
    </header>
  );
}

import {
  Boxes,
  Clock,
  Cpu,
  Download,
  FileCode,
  FileLock,
  Flame,
  LayoutDashboard,
  ScrollText,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import logoUrl from "@/images/logo.png";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

import { ThemeToggle } from "./ThemeToggle";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/system", label: "System", icon: Cpu },
  { to: "/services", label: "Services", icon: Settings2 },
  { to: "/docker", label: "Docker", icon: Boxes },
  { to: "/cron", label: "Cron", icon: Clock },
  { to: "/scripts", label: "Scripts", icon: FileCode },
  { to: "/audit", label: "Audit", icon: ShieldCheck },
  { to: "/firewall", label: "Firewall", icon: Flame },
  { to: "/updates", label: "Updates", icon: Download },
  { to: "/permissions", label: "Permissions", icon: FileLock },
  { to: "/logs", label: "Logs", icon: ScrollText },
];

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-card flex flex-col">
      <div className="p-4 flex items-center gap-2.5">
        <img
          src={logoUrl}
          alt="MonitShark"
          className="size-9 rounded-md object-contain shrink-0"
        />
        <div className="font-semibold tracking-tight">MonitShark</div>
      </div>
      <Separator />
      <nav className="flex-1 p-2 space-y-1">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )
            }
          >
            <Icon className="size-4" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <Separator />
      <div className="p-3 flex items-center justify-between">
        <span className="text-xs text-muted-foreground font-mono">v0.1.0</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}

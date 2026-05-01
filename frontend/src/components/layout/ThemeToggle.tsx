import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTheme } from "@/theme/provider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
      {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}

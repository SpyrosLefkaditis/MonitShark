import { Sparkles } from "lucide-react";

import { useChat } from "@/chat/ChatProvider";
import { Button } from "@/components/ui/button";

type Props = {
  path: string;
  lines: number;
  disabled?: boolean;
};

export function AnalyzeButton({ path, lines, disabled }: Props) {
  const { prefill, openDrawer } = useChat();
  const onClick = () => {
    prefill(`Analyze the last ${lines} lines of ${path} for security issues.`);
    openDrawer();
  };
  return (
    <Button variant="outline" size="sm" onClick={onClick} disabled={disabled} className="gap-1.5">
      <Sparkles className="size-3.5" />
      Ask MonitShark to analyze
    </Button>
  );
}

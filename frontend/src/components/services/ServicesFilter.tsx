import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type StateFilter = "all" | "active" | "inactive";

type Props = {
  query: string;
  onQueryChange: (q: string) => void;
  state: StateFilter;
  onStateChange: (s: StateFilter) => void;
  total: number;
  shown: number;
};

export function ServicesFilter({
  query,
  onQueryChange,
  state,
  onStateChange,
  total,
  shown,
}: Props) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search by name or description…"
          className="pl-8"
        />
      </div>
      <Select value={state} onValueChange={(v) => onStateChange(v as StateFilter)}>
        <SelectTrigger className="w-full sm:w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="active">Active only</SelectItem>
          <SelectItem value="inactive">Inactive only</SelectItem>
        </SelectContent>
      </Select>
      <div className="text-xs text-muted-foreground font-mono whitespace-nowrap">
        {shown} / {total}
      </div>
    </div>
  );
}

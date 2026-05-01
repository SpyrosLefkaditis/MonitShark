import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Props = {
  value: string;
  onChange: (path: string) => void;
  paths: string[];
  disabled?: boolean;
};

export function LogFileSelect({ value, onChange, paths, disabled }: Props) {
  return (
    <Select value={value || undefined} onValueChange={onChange} disabled={disabled || paths.length === 0}>
      <SelectTrigger className="w-full sm:w-[28rem]">
        <SelectValue placeholder={paths.length === 0 ? "No log paths available" : "Choose a log file…"} />
      </SelectTrigger>
      <SelectContent>
        {paths.map((p) => (
          <SelectItem key={p} value={p}>
            <span className="font-mono text-xs">{p}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

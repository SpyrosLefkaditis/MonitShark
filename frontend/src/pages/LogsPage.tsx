import { isAxiosError } from "axios";
import { RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { AnalyzeButton } from "@/components/logs/AnalyzeButton";
import { LogFileSelect } from "@/components/logs/LogFileSelect";
import { LogViewer } from "@/components/logs/LogViewer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useLogSearch, useLogSources, useLogTail } from "@/hooks/useLogs";

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

export function LogsPage() {
  const sources = useLogSources();
  const [path, setPath] = useState<string>("");
  const [lines, setLines] = useState<number>(200);
  const [searchQuery, setSearchQuery] = useState("");
  const [regex, setRegex] = useState(false);
  const [searchMatches, setSearchMatches] = useState<string[] | null>(null);

  // Default to first available source once known.
  useEffect(() => {
    if (!path && sources.data?.paths.length) {
      setPath(sources.data.paths[0]);
    }
  }, [sources.data, path]);

  const tail = useLogTail(path || null, lines);
  const search = useLogSearch();

  const onRefresh = () => {
    if (path) tail.refetch();
  };

  const onSearch = async () => {
    if (!path || !searchQuery.trim()) return;
    try {
      const r = await search.mutateAsync({
        path,
        query: searchQuery,
        regex,
        max_matches: 200,
      });
      setSearchMatches(r.matches);
      toast.success(`Search complete · ${r.matches.length} matches`);
    } catch (e) {
      toast.error("Search failed.", { description: describeError(e) });
    }
  };

  const onClearSearch = () => {
    setSearchMatches(null);
    setSearchQuery("");
  };

  const tailLines = tail.data?.lines ?? [];
  const linesToShow = searchMatches ?? tailLines;

  const sanitizedLines = useMemo(() => {
    const n = Number(lines);
    if (!Number.isFinite(n) || n <= 0) return 200;
    return Math.min(2000, Math.max(1, Math.floor(n)));
  }, [lines]);

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Log files</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div className="flex-1 space-y-1.5">
              <Label className="text-xs text-muted-foreground">File</Label>
              <LogFileSelect
                value={path}
                onChange={(p) => {
                  setPath(p);
                  setSearchMatches(null);
                }}
                paths={sources.data?.paths ?? []}
                disabled={sources.isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Lines</Label>
              <Input
                type="number"
                min={1}
                max={2000}
                value={lines}
                onChange={(e) => setLines(Number(e.target.value) || 200)}
                onBlur={() => setLines(sanitizedLines)}
                className="w-32 font-mono"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={!path || tail.isFetching}
                className="gap-1.5"
              >
                <RefreshCw className={tail.isFetching ? "size-3.5 animate-spin" : "size-3.5"} />
                Refresh
              </Button>
              <AnalyzeButton path={path} lines={sanitizedLines} disabled={!path} />
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div className="flex-1 space-y-1.5">
              <Label className="text-xs text-muted-foreground">Search this file</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      onSearch();
                    }
                  }}
                  placeholder="failed password, sshd, rate limit…"
                  className="pl-8"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-border px-3 h-9">
              <Switch id="logs-regex" checked={regex} onCheckedChange={setRegex} />
              <Label htmlFor="logs-regex" className="text-xs cursor-pointer">
                regex
              </Label>
            </div>
            <Button
              size="sm"
              onClick={onSearch}
              disabled={!path || !searchQuery.trim() || search.isPending}
            >
              {search.isPending ? "Searching…" : "Search"}
            </Button>
            {searchMatches !== null && (
              <Button size="sm" variant="ghost" onClick={onClearSearch}>
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="font-mono text-sm">
            {path || "—"}
            {searchMatches !== null && (
              <span className="ml-2 text-xs text-muted-foreground font-normal">
                · {searchMatches.length} matches
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!path ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Select a log file above to begin tailing.
            </div>
          ) : tail.isLoading && !tail.data ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-4" />
              ))}
            </div>
          ) : tail.error ? (
            <div className="py-10 text-center text-sm text-destructive">
              Failed to load logs. {(tail.error as Error).message}
            </div>
          ) : (
            <LogViewer lines={linesToShow} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

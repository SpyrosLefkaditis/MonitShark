import { isAxiosError } from "axios";
import { ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { AuditRunner } from "@/components/audit/AuditRunner";
import { FindingsGroup } from "@/components/audit/FindingsGroup";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useApplyFix,
  useDismissFinding,
  useFindings,
  useRunAllAudits,
} from "@/hooks/useAudit";
import type { Finding } from "@/types";

function describeError(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string })?.detail;
    return detail ?? e.message;
  }
  return (e as Error).message ?? "Unknown error";
}

export function AuditPage() {
  const findings = useFindings("open");
  const runAll = useRunAllAudits();
  const apply = useApplyFix();
  const dismiss = useDismissFinding();

  const [lastRunAt, setLastRunAt] = useState<number | null>(null);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [dismissingId, setDismissingId] = useState<string | null>(null);

  const groups = useMemo(() => {
    const all = findings.data ?? [];
    const byCategory = new Map<string, Finding[]>();
    for (const f of all) {
      const list = byCategory.get(f.category) ?? [];
      list.push(f);
      byCategory.set(f.category, list);
    }
    return Array.from(byCategory.entries())
      .map(([category, items]) => ({ category, items }))
      .sort((a, b) => a.category.localeCompare(b.category));
  }, [findings.data]);

  const totalFindings = findings.data?.length ?? null;

  const onRun = async () => {
    try {
      const result = await runAll.mutateAsync();
      setLastRunAt(Date.now());
      toast.success(`Audit complete · ${result.total_findings} findings`);
    } catch (e) {
      toast.error("Audit failed.", { description: describeError(e) });
    }
  };

  const onApply = async (id: string) => {
    setApplyingId(id);
    try {
      const r = await apply.mutateAsync(id);
      if (r.ok) {
        toast.success("Fix applied.", { description: r.message });
      } else {
        toast.message("Fix not applied", {
          description: r.message || "Phase 7 will wire real fixes.",
        });
      }
    } catch (e) {
      toast.error("Apply fix failed.", { description: describeError(e) });
    } finally {
      setApplyingId(null);
    }
  };

  const onDismiss = async (id: string) => {
    setDismissingId(id);
    try {
      await dismiss.mutateAsync(id);
      toast.success("Finding dismissed.");
    } catch (e) {
      toast.error("Dismiss failed.", { description: describeError(e) });
    } finally {
      setDismissingId(null);
    }
  };

  const isEmpty = !findings.isLoading && groups.length === 0;

  return (
    <div className="grid gap-4">
      <Card>
        <CardContent className="p-4">
          <AuditRunner
            onRun={onRun}
            pending={runAll.isPending}
            totalFindings={totalFindings}
            lastRunAt={lastRunAt}
          />
        </CardContent>
      </Card>

      {isEmpty ? (
        <Card>
          <CardContent className="p-10 flex flex-col items-center text-center gap-3">
            <div className="size-10 rounded-md bg-primary/15 grid place-items-center text-primary">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <p className="text-sm font-medium">No findings yet.</p>
              <p className="text-xs text-muted-foreground mt-1">
                Click <span className="font-medium">Run full audit</span> to scan SSH, users,
                permissions, and packages.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-4">
            {groups.length > 0 ? (
              <Tabs defaultValue={groups[0].category}>
                <TabsList className="flex-wrap h-auto">
                  {groups.map(({ category, items }) => (
                    <TabsTrigger key={category} value={category} className="gap-2">
                      <span className="capitalize">{category}</span>
                      <span className="text-[10px] font-mono rounded-sm bg-muted px-1.5 py-0.5">
                        {items.length}
                      </span>
                    </TabsTrigger>
                  ))}
                </TabsList>
                {groups.map(({ category, items }) => (
                  <TabsContent key={category} value={category} className="mt-4">
                    <FindingsGroup
                      category={category}
                      findings={items}
                      onApply={onApply}
                      onDismiss={onDismiss}
                      applyingId={applyingId}
                      dismissingId={dismissingId}
                    />
                  </TabsContent>
                ))}
              </Tabs>
            ) : (
              <div className="py-10 text-center text-sm text-muted-foreground">
                Loading findings…
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

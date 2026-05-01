import { isAxiosError } from "axios";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ServiceActionDialog } from "@/components/services/ServiceActionDialog";
import { ServicesFilter, type StateFilter } from "@/components/services/ServicesFilter";
import { ServicesTable } from "@/components/services/ServicesTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useServiceAction, useServices } from "@/hooks/useServices";
import type { ServiceAction, ServiceItem } from "@/types";

export function ServicesPage() {
  const { data, isLoading, error } = useServices("all");
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");
  const [pending, setPending] = useState<{ svc: ServiceItem; action: ServiceAction } | null>(null);

  const action = useServiceAction();

  const filtered = useMemo(() => {
    const all = data ?? [];
    const q = query.trim().toLowerCase();
    return all.filter((s) => {
      if (stateFilter === "active" && s.active_state !== "active") return false;
      if (stateFilter === "inactive" && s.active_state === "active") return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        (s.description ?? "").toLowerCase().includes(q)
      );
    });
  }, [data, query, stateFilter]);

  const onConfirm = async () => {
    if (!pending) return;
    try {
      const result = await action.mutateAsync({
        name: pending.svc.name,
        action: pending.action,
      });
      if (result.ok) {
        toast.success(`${pending.action} ${pending.svc.name}`, {
          description: result.output ? result.output.slice(0, 200) : undefined,
        });
      } else {
        toast.error(`Failed to ${pending.action} ${pending.svc.name}`, {
          description: result.output ? result.output.slice(0, 200) : undefined,
        });
      }
    } catch (e) {
      const msg = isAxiosError(e)
        ? (e.response?.data as { detail?: string })?.detail ?? e.message
        : (e as Error).message;
      toast.error(`Failed to ${pending.action} ${pending.svc.name}`, { description: msg });
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Services</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ServicesFilter
            query={query}
            onQueryChange={setQuery}
            state={stateFilter}
            onStateChange={setStateFilter}
            total={data?.length ?? 0}
            shown={filtered.length}
          />
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : error ? (
            <div className="py-10 text-center text-sm text-destructive">
              Failed to load services. {(error as Error).message}
            </div>
          ) : (
            <ServicesTable
              services={filtered}
              onAction={(svc, a) => setPending({ svc, action: a })}
            />
          )}
        </CardContent>
      </Card>

      <ServiceActionDialog
        open={!!pending}
        onOpenChange={(o) => !o && setPending(null)}
        service={pending?.svc.name ?? null}
        action={pending?.action ?? null}
        onConfirm={onConfirm}
        pending={action.isPending}
      />
    </div>
  );
}

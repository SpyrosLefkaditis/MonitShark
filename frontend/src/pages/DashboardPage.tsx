import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardPage() {
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Dashboard</CardTitle>
          <CardDescription>
            Live host metrics, top processes, and active alerts. Wiring lands in Phase 4 (REST) and
            Phase 5 (live WebSocket).
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

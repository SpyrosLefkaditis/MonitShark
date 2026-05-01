import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LogsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Logs</CardTitle>
        <CardDescription>
          Tail and search /var/log files. The "Ask agent to analyze" handoff lands in Phase 6.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

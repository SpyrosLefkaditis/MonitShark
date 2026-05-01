import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function AuditPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit</CardTitle>
        <CardDescription>
          Run security audits across SSH, users, permissions, and packages. Findings + apply-fix in
          Phase 4; agent-driven audits in Phases 6–7.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

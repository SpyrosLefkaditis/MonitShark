import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function NotFoundPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Not found</CardTitle>
        <CardDescription>That route doesn't exist (yet).</CardDescription>
      </CardHeader>
      <div className="px-6 pb-6">
        <Button asChild variant="outline" size="sm">
          <Link to="/">Back to dashboard</Link>
        </Button>
      </div>
    </Card>
  );
}

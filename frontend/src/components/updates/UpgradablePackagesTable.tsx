import { Badge } from "@/components/ui/badge";
import type { UpgradablePackage } from "@/types";

type Props = {
  packages: UpgradablePackage[];
};

export function UpgradablePackagesTable({ packages }: Props) {
  if (packages.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        No upgradable packages detected.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-2 px-3 font-medium">Package</th>
            <th className="py-2 px-3 font-medium">Current</th>
            <th className="py-2 px-3 font-medium">New</th>
            <th className="py-2 px-3 font-medium">Source</th>
          </tr>
        </thead>
        <tbody>
          {packages.map((p) => (
            <tr
              key={`${p.package}-${p.arch}-${p.new_version}`}
              className="border-b border-border/60 last:border-b-0 hover:bg-accent/40"
            >
              <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">
                {p.package}
                {p.arch ? <span className="text-muted-foreground">.{p.arch}</span> : null}
              </td>
              <td className="py-2 px-3 font-mono text-xs text-muted-foreground">
                {p.current_version || "—"}
              </td>
              <td className="py-2 px-3 font-mono text-xs">{p.new_version}</td>
              <td className="py-2 px-3">
                {p.is_security ? (
                  <Badge variant="destructive">security</Badge>
                ) : (
                  <span className="font-mono text-xs text-muted-foreground">{p.source}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

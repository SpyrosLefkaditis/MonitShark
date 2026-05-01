// Shared TypeScript types mirroring backend pydantic schemas (backend/app/schemas.py).

export type CpuMetric = {
  percent: number;
  count: number;
  load_1: number;
  load_5: number;
  load_15: number;
};

export type MemoryMetric = {
  total: number;
  used: number;
  available: number;
  percent: number;
};

export type DiskMetric = {
  mountpoint: string;
  total: number;
  used: number;
  free: number;
  percent: number;
};

export type NetMetric = {
  bytes_sent: number;
  bytes_recv: number;
  packets_sent: number;
  packets_recv: number;
};

export type ProcessItem = {
  pid: number;
  name: string;
  user: string | null;
  cpu_percent: number;
  mem_percent: number;
  rss: number;
  cmdline: string;
};

export type MetricsSnapshot = {
  ts: number;
  cpu: CpuMetric;
  memory: MemoryMetric;
  disks: DiskMetric[];
  net: NetMetric;
  top_processes: ProcessItem[];
};

export type ServiceItem = {
  name: string;
  description: string;
  load_state: string;
  active_state: string;
  sub_state: string;
  enabled: string | null;
};

export type ServiceAction = "start" | "stop" | "restart" | "reload";

export type CronEntry = {
  id: string;
  user: string;
  schedule: string;
  command: string;
  comment: string | null;
  enabled: boolean;
};

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export type FindingStatus = "open" | "fixed" | "dismissed";

export type Finding = {
  id: string;
  category: string;
  severity: Severity;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  fix_id: string | null;
  status: FindingStatus;
  created_at?: number;
};

export type AuditReport = {
  name: string;
  findings: Finding[];
};

export type AuditAggregate = {
  reports: AuditReport[];
  total_findings: number;
};

export type AlertKind = "threshold" | "finding";

export type Alert = {
  id: number;
  kind: AlertKind;
  severity: Severity;
  title: string;
  body: string;
  created_at: number;
  acknowledged_at: number | null;
};

export type LogSources = { paths: string[] };

export type LogTail = { path: string; lines: string[] };

export type LogSearchResult = { path: string; matches: string[] };

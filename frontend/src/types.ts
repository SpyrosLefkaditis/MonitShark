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

export type FirewallAction = "ALLOW" | "DENY" | "REJECT" | "LIMIT";

export type FirewallRule = {
  to: string;
  action: FirewallAction;
  from: string;
  proto: "tcp" | "udp" | null;
  comment: string | null;
};

export type FirewallStatus = {
  installed: boolean;
  active?: boolean;
  default_incoming?: string;
  default_outgoing?: string;
  rules?: FirewallRule[];
};

export type FirewallActionResult = { ok: boolean; output: string };

export type FirewallRuleInput = {
  action: "allow" | "deny" | "reject" | "limit";
  port: number | string;
  proto?: "tcp" | "udp" | null;
  source?: string | null;
  comment?: string | null;
};

export type UpgradablePackage = {
  package: string;
  current_version: string;
  new_version: string;
  arch: string;
  source: string;
  is_security: boolean;
};

export type UpdatesList = {
  package_manager: "apt" | "dnf" | "unknown";
  total: number;
  security_count: number;
  packages: UpgradablePackage[];
};

export type UpgradeResult = {
  ok: boolean;
  rc: number;
  stdout: string;
  stderr: string;
};

// --- Scripts ---
export type ScriptFile = {
  name: string;
  size_bytes: number;
  modified_at: number;
  executable: boolean;
};

export type ScriptContent = {
  name: string;
  content: string;
  modified_at: number;
};

export type ScriptRunResult = {
  name: string;
  rc: number;
  stdout: string;
  stderr: string;
  timeout_s: number;
};

export type ScriptInstallServiceResult = {
  script: string;
  service: string;
  unit_path: string;
  daemon_reload_rc: number;
  daemon_reload_stderr: string;
};

export type ScriptScheduleResult = {
  script: string;
  user: string;
  schedule: string;
  command: string;
  tabfile: string;
  scheduled_at: number;
};

// --- File permissions ---
export type FsEntry = {
  name: string;
  is_dir: boolean;
  is_link: boolean;
  mode: number;
  mode_octal: string;
  owner: string;
  group: string;
  uid: number;
  gid: number;
  size: number;
  mtime: number;
};

export type FsListing = {
  path: string;
  entries: FsEntry[];
  total: number;
  truncated: boolean;
  roots: string[];
};

export type FsInfo = FsEntry & { path: string };

// --- Docker container monitor ---
export type DockerPort = {
  container_port: string;
  proto: string;
  host_ip: string | null;
  host_port: string | null;
};

export type DockerMount = {
  type: string | null;
  source: string | null;
  destination: string | null;
  mode: string | null;
  rw: boolean | null;
};

export type DockerNetwork = {
  ip_address: string | null;
  gateway: string | null;
  mac_address: string | null;
  network_id: string | null;
};

export type DockerEnvVar = { key: string; value: string };

export type DockerContainer = {
  id: string;
  short_id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  created: string | null;
  ports: DockerPort[];
  labels: Record<string, string>;
  health: string | null;
};

export type DockerContainerDetail = DockerContainer & {
  image_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  command: string[];
  entrypoint: string[];
  working_dir: string | null;
  user: string | null;
  env: DockerEnvVar[];
  mounts: DockerMount[];
  network_mode: string | null;
  networks: Record<string, DockerNetwork>;
  restart_policy: Record<string, unknown>;
};

export type DockerStats = {
  id: string;
  short_id: string;
  name: string;
  ts: number;
  cpu_percent: number;
  online_cpus: number;
  memory_usage: number;
  memory_limit: number;
  memory_percent: number;
  net_rx: number;
  net_tx: number;
  block_read: number;
  block_write: number;
};

export type DockerAction =
  | "start"
  | "stop"
  | "restart"
  | "pause"
  | "unpause"
  | "kill";

export type DockerActionResult = {
  ok: boolean;
  state: string;
  id: string;
  name: string;
};

export type DockerLogFrame =
  | { type: "log"; line: string; ts: number }
  | { type: "error"; message: string };

// --- Extended system stats ---
export type HostInfo = {
  kernel: string;
  kernel_version: string;
  distro: string;
  distro_version: string;
  hostname: string;
  boot_time: number;
  uptime_seconds: number;
  cpu_model: string;
  arch: string;
  total_ram_bytes: number;
  cpu_cores_physical: number;
  cpu_cores_logical: number;
};

export type CpuCore = {
  core: number;
  percent: number;
  freq_mhz: number | null;
};

export type DiskIO = {
  name: string;
  read_mb_s: number;
  write_mb_s: number;
  read_iops: number;
  write_iops: number;
  busy_percent: number | null;
};

export type NetIface = {
  name: string;
  bytes_recv_per_sec: number;
  bytes_sent_per_sec: number;
  packets_recv_per_sec: number;
  packets_sent_per_sec: number;
  errors_in: number;
  errors_out: number;
  drops_in: number;
  drops_out: number;
  is_virtual: boolean;
};

export type Sensor = {
  kind: "temperature" | "fan" | "battery";
  chip: string;
  label: string;
  current: number;
  high: number | null;
  critical: number | null;
  unit: string;
  secsleft?: number | null;
  power_plugged?: boolean;
};

export type KernelModule = {
  name: string;
  size: number;
  used_count: number;
};

export type ListeningPort = {
  laddr: string;
  proto: string;
  pid: number | null;
  process: string;
};

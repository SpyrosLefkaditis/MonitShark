"""Shared response/request schemas. Used by routes AND by agent tool outputs."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Health ---
class HealthOut(BaseModel):
    ok: bool = True
    version: str
    uptime_s: float


# --- Metrics ---
class CpuMetric(BaseModel):
    percent: float
    count: int
    load_1: float
    load_5: float
    load_15: float


class MemoryMetric(BaseModel):
    total: int
    used: int
    available: int
    percent: float


class DiskMetric(BaseModel):
    mountpoint: str
    total: int
    used: int
    free: int
    percent: float


class NetMetric(BaseModel):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


class ProcessItem(BaseModel):
    pid: int
    name: str
    user: str | None = None
    cpu_percent: float
    mem_percent: float
    rss: int
    cmdline: str = ""


class MetricsSnapshot(BaseModel):
    ts: float
    cpu: CpuMetric
    memory: MemoryMetric
    disks: list[DiskMetric]
    net: NetMetric
    top_processes: list[ProcessItem]


# --- Services ---
class ServiceItem(BaseModel):
    name: str
    description: str = ""
    load_state: str = ""
    active_state: str = ""
    sub_state: str = ""
    enabled: str | None = None


ServiceAction = Literal["start", "stop", "restart", "reload"]


class ServiceActionIn(BaseModel):
    action: ServiceAction


class ServiceActionOut(BaseModel):
    ok: bool
    output: str = ""


# --- Cron ---
class CronEntry(BaseModel):
    id: str  # synthesized identifier: f"{user}::{idx}"
    user: str
    schedule: str
    command: str
    comment: str | None = None
    enabled: bool = True


class CronCreateIn(BaseModel):
    user: str = "root"
    schedule: str
    command: str
    comment: str | None = None


class CronUpdateIn(BaseModel):
    schedule: str | None = None
    command: str | None = None
    comment: str | None = None
    enabled: bool | None = None


class CronRunIn(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    timeout_s: int = 60


class CronRunOut(BaseModel):
    rc: int
    stdout: str
    stderr: str


# --- Logs ---
class LogTailOut(BaseModel):
    path: str
    lines: list[str]


class LogSearchIn(BaseModel):
    path: str
    query: str
    regex: bool = False
    max_matches: int = 200


class LogSearchOut(BaseModel):
    path: str
    matches: list[str]


class LogSourcesOut(BaseModel):
    paths: list[str]


# --- Audits / Findings ---
Severity = Literal["info", "low", "medium", "high", "critical"]
FindingStatus = Literal["open", "fixed", "dismissed"]


class Finding(BaseModel):
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    fix_id: str | None = None
    status: FindingStatus = "open"
    created_at: float | None = None


class AuditReport(BaseModel):
    name: str
    findings: list[Finding]


class AuditAggregate(BaseModel):
    reports: list[AuditReport]
    total_findings: int


# --- Alerts ---
AlertKind = Literal["threshold", "finding"]


class Alert(BaseModel):
    id: int
    kind: AlertKind
    severity: Severity
    title: str
    body: str
    created_at: float
    acknowledged_at: float | None = None


class AckOut(BaseModel):
    ok: bool


# --- Chat (used by agent routes) ---
class ChatMessageIn(BaseModel):
    message: str
    thread_id: str | None = None


class ChatMessageOut(BaseModel):
    thread_id: str
    text: str

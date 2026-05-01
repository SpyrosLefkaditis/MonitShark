"""LangChain @tool wrappers exposing the read-only host inspection surface to
the agent. Every tool is a thin pydantic-validated facade over the existing
backend modules, so the agent and the REST API share the same implementations.

Phase 7 will add destructive tools (kill_process, service_action, create_cron,
delete_cron, run_script, create_user, apply_fix, acknowledge_alert) gated by a
LangGraph `interrupt()` node.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app import cron as cron_mod
from app import logs as logs_mod
from app import metrics as metrics_mod
from app import services as services_mod
from app.audits import REGISTRY as AUDITS
from app.schemas import LogSearchIn


def _dump(model_or_obj: Any) -> Any:
    if hasattr(model_or_obj, "model_dump"):
        return model_or_obj.model_dump()
    return model_or_obj


@tool
def get_metrics() -> dict:
    """Return a compact snapshot of the host's current resource usage: CPU%, memory%,
    disk usage per partition, network throughput. (Use list_processes() separately if you
    need top processes — keeps this response small.)"""
    snap = metrics_mod.snapshot()
    return {
        "cpu": {
            "percent": round(snap.cpu.percent, 1),
            "count": snap.cpu.count,
            "load_1": snap.cpu.load_1,
            "load_5": snap.cpu.load_5,
            "load_15": snap.cpu.load_15,
        },
        "memory": {
            "percent": round(snap.memory.percent, 1),
            "used_mb": round(snap.memory.used / (1024 * 1024)),
            "total_mb": round(snap.memory.total / (1024 * 1024)),
        },
        "disks": [
            {"mount": d.mountpoint, "percent": round(d.percent, 1),
             "used_gb": round(d.used / (1024 ** 3), 1), "total_gb": round(d.total / (1024 ** 3), 1)}
            for d in snap.disks
        ],
        "net": {
            "bytes_sent_mb": round(snap.net.bytes_sent / (1024 * 1024), 1),
            "bytes_recv_mb": round(snap.net.bytes_recv / (1024 * 1024), 1),
        },
    }


@tool
def list_processes(top: int = 10) -> list[dict]:
    """List the top N processes by CPU usage. Returns pid, name, user, cpu_percent, mem_percent, rss.
    Default 10. Cap 25. Use this when investigating "what's using my CPU?" type questions."""
    snap = metrics_mod.snapshot()
    procs = snap.top_processes[: max(1, min(top, 25))]
    # Trim each process to the fields the LLM actually needs.
    return [
        {
            "pid": p.pid, "name": p.name, "user": p.user,
            "cpu_percent": round(p.cpu_percent, 1),
            "mem_percent": round(p.mem_percent, 1),
            "rss_mb": round(p.rss / (1024 * 1024), 1),
        }
        for p in procs
    ]


@tool
def list_services(only_active: bool = True, limit: int = 40, name_contains: str | None = None) -> dict:
    """List systemd .service units on the host with their state.
    Defaults to active services only; pass only_active=False to also see inactive/dead.
    Returns a compact summary: total count + per-state counts + a sample list (capped at limit).
    Use name_contains to filter by substring (e.g. "ssh", "cron", "nginx") — best for narrowing
    to a few units of interest. Use get_service(name) for full detail on one unit."""
    units = services_mod.list_units()
    if only_active:
        units = [u for u in units if u.active_state == "active"]
    if name_contains:
        needle = name_contains.lower()
        units = [u for u in units if needle in u.name.lower()]
    by_state: dict[str, int] = {}
    for u in units:
        by_state[u.active_state] = by_state.get(u.active_state, 0) + 1
    sample = [
        {"name": u.name, "active": u.active_state, "sub": u.sub_state}
        for u in units[: max(1, min(limit, 100))]
    ]
    return {
        "total_returned": len(units),
        "by_state": by_state,
        "sample": sample,
        "note": "Use get_service(name) for full detail (description, enabled, journal).",
    }


@tool
def get_service(name: str) -> dict:
    """Get detail for a single systemd service: load/active/sub state, enabled flag, and the last 50 journal lines.
    Use this to investigate WHY a service is failing or what it just logged."""
    return services_mod.detail(name)


@tool
def list_cron(user: str | None = None) -> list[dict]:
    """List cron entries on the host. Per-user spool tabs + system-wide /etc/crontab.
    Pass user="root" (or any username) to filter to one user's tab."""
    return [_dump(c) for c in cron_mod.list_all(user=user)]


@tool
def list_log_sources() -> list[str]:
    """List the log files under /var/log/ that exist on this host (auth.log, syslog, dpkg.log, dnf.log, messages, secure)."""
    return logs_mod.list_sources()


@tool
def tail_log(path: str = "/var/log/syslog", lines: int = 200) -> dict:
    """Return the last N lines of a log file under /var/log/. lines is capped at 2000."""
    out = logs_mod.tail(path, max(1, min(lines, 2000)))
    return _dump(out)


@tool
def search_log(path: str, query: str, regex: bool = False, max_matches: int = 100) -> dict:
    """Search a log file under /var/log/ for lines matching `query`. Set regex=True to interpret query as a regex.
    Returns matches list (capped at max_matches)."""
    out = logs_mod.search(LogSearchIn(path=path, query=query, regex=regex, max_matches=max(1, min(max_matches, 1000))))
    return _dump(out)


@tool
async def audit_ssh() -> dict:
    """Audit the host's SSH server configuration (/etc/ssh/sshd_config) for risky settings:
    PermitRootLogin, PasswordAuthentication, PermitEmptyPasswords, weak ciphers/MACs, etc."""
    return _dump(await AUDITS["ssh"]())


@tool
async def audit_users() -> dict:
    """Audit the host's user accounts: duplicate UID 0 entries, passwordless accounts, sudoers grants without password."""
    return _dump(await AUDITS["users"]())


@tool
async def audit_permissions() -> dict:
    """Audit world-writable files in /etc, world-readable secrets, /etc/shadow mode, and unexpected SUID-root binaries."""
    return _dump(await AUDITS["permissions"]())


@tool
async def audit_packages() -> dict:
    """Check for pending OS package updates (security updates flagged separately). Distro-aware: apt vs dnf."""
    return _dump(await AUDITS["packages"]())


@tool
async def run_full_audit() -> dict:
    """Run every security audit (ssh, users, permissions, packages) and return all findings grouped by category.
    Use this for a complete posture check."""
    out: dict[str, Any] = {}
    for name, fn in AUDITS.items():
        try:
            out[name] = _dump(await fn())
        except Exception as e:
            out[name] = {"name": name, "error": repr(e)}
    return out


# Ordered list passed to ChatGroq.bind_tools — the order roughly suggests
# which tools the model should reach for first.
TOOLS = [
    get_metrics,
    list_processes,
    list_services,
    get_service,
    list_cron,
    list_log_sources,
    tail_log,
    search_log,
    audit_ssh,
    audit_users,
    audit_permissions,
    audit_packages,
    run_full_audit,
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def stringify_tool_output(result: Any) -> str:
    """Convert a tool's return value to a string suitable for ToolMessage content.
    Caps payload to keep token counts sane (large audit reports can be ~50KB)."""
    if isinstance(result, str):
        s = result
    else:
        try:
            s = json.dumps(result, default=str)
        except (TypeError, ValueError):
            s = str(result)
    if len(s) > 6_000:
        s = s[:6_000] + "\n…[truncated]"
    return s

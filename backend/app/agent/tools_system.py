"""Read-only @tool wrappers around app.system_stats for the LangGraph agent."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app import system_stats as ss


def _safe(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool
def system_host_info() -> dict:
    """Return host-level metadata: kernel version, distro pretty name + version,
    hostname, uptime in seconds, CPU model, architecture, total RAM bytes,
    physical + logical core counts."""
    return _safe(ss.host_info)


@tool
def system_cpu_per_core(interval: float = 0.0) -> list[dict]:
    """Return per-CPU utilization (percent) and per-core frequency (MHz). Pass
    interval>0 (in seconds) to take a blocking measurement window; 0 returns
    the value computed against the previous call."""
    try:
        return ss.cpu_per_core(interval=float(interval or 0.0))
    except Exception:
        return []


@tool
def system_disk_io_per_disk() -> list[dict]:
    """Per-disk I/O rates (read/write MB/s, read/write IOPS, busy%) computed
    against the previous call. Call twice with a short pause between calls
    to get a meaningful rate on the second invocation."""
    try:
        return ss.disk_io_per_disk()
    except Exception:
        return []


@tool
def system_net_per_iface(include_virtual: bool = False) -> list[dict]:
    """Per-network-interface throughput (bytes/sec, packets/sec, errors, drops)
    computed against the previous call. Skips loopback + container/bridge
    interfaces by default; pass include_virtual=True to include them."""
    try:
        return ss.net_per_iface(include_virtual=bool(include_virtual))
    except Exception:
        return []


@tool
def system_sensors() -> list[dict]:
    """Return temperatures (Celsius), fans (RPM), and battery (%) from the
    host's hwmon sensors. Empty list when the host has none configured."""
    try:
        return ss.sensors()
    except Exception:
        return []


@tool
def system_kernel_modules() -> list[dict]:
    """Return up to 200 loaded kernel modules parsed from /proc/modules.
    Each entry: name, size in bytes, use_count."""
    try:
        return ss.kernel_modules()
    except Exception:
        return []


@tool
def system_listening_ports() -> list[dict]:
    """Return TCP/UDP sockets currently in LISTEN state. Each entry: laddr
    (host:port), proto (tcp4/tcp6/udp4/udp6), pid (when available), and
    process name."""
    try:
        return ss.listening_ports()
    except Exception:
        return []


TOOLS = [
    system_host_info,
    system_cpu_per_core,
    system_disk_io_per_disk,
    system_net_per_iface,
    system_sensors,
    system_kernel_modules,
    system_listening_ports,
]

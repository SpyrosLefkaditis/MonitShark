"""Extended system telemetry — separate from app.metrics.

Provides:
  * host_info()        — kernel, distro, hostname, uptime, CPU model, RAM, cores.
  * cpu_per_core()     — per-CPU utilization + per-core frequency.
  * disk_io_per_disk() — per-disk MB/s + IOPS + busy% deltas vs previous call.
  * net_per_iface()    — per-NIC byte/packet/error/drop rates vs previous call.
  * sensors()          — temperatures + fans + battery from psutil.
  * kernel_modules()   — parsed /proc/modules entries (capped at 200).
  * listening_ports()  — psutil net_connections filtered to LISTEN.

The disk and network helpers cache the previous sample in module state so the
rate is computed against the wall-clock interval since the previous call.
"""
from __future__ import annotations

import os
import platform
import re
import time
from pathlib import Path
from threading import Lock
from typing import Any

import psutil

from app.config import settings

_VIRTUAL_IFACE_PREFIXES: tuple[str, ...] = (
    "lo",
    "docker",
    "br-",
    "veth",
    "virbr",
    "vmnet",
    "tun",
    "tap",
    "wg",
    "cni",
    "flannel",
    "kube",
)

# Module-level rate caches.
_disk_lock = Lock()
_disk_prev: dict[str, tuple[float, Any]] = {}
_net_lock = Lock()
_net_prev: dict[str, tuple[float, Any]] = {}


def _host_path(*parts: str) -> Path:
    """Join under HOST_ROOT when present (container view) else absolute root."""
    root = (settings.host_root or "/").rstrip("/") or "/"
    return Path(root, *parts) if root != "/" else Path("/", *parts)


def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except (OSError, PermissionError):
        return ""


def _parse_os_release(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip().strip('"').strip("'")
        out[key.strip()] = val
    return out


def _cpu_model() -> str:
    text = _read_text_safe(_host_path("proc", "cpuinfo"))
    if not text:
        return ""
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            _, _, val = line.partition(":")
            return val.strip()
    # ARM kernels expose "Hardware" instead of "model name".
    for line in text.splitlines():
        if line.lower().startswith("hardware"):
            _, _, val = line.partition(":")
            return val.strip()
    return ""


def host_info() -> dict[str, Any]:
    """Compact host description used by the System overview card."""
    uname = os.uname()
    boot = float(psutil.boot_time())
    now = time.time()
    uptime = max(0.0, now - boot)

    os_release = _parse_os_release(_read_text_safe(_host_path("etc", "os-release")))
    pretty = (os_release.get("PRETTY_NAME")
              or os_release.get("NAME")
              or platform.platform()).strip()
    distro_version = (os_release.get("VERSION_ID")
                      or os_release.get("VERSION")
                      or "").strip()

    hostname = os_release.get("HOSTNAME") or uname.nodename
    # /etc/hostname (host view) is more authoritative when running in a container.
    htxt = _read_text_safe(_host_path("etc", "hostname")).strip()
    if htxt:
        hostname = htxt

    try:
        total_ram = int(psutil.virtual_memory().total)
    except Exception:
        total_ram = 0

    physical = psutil.cpu_count(logical=False) or 0
    logical = psutil.cpu_count(logical=True) or 0

    return {
        "kernel": f"{uname.sysname} {uname.release}",
        "kernel_version": uname.version,
        "distro": pretty,
        "distro_version": distro_version,
        "hostname": hostname,
        "boot_time": boot,
        "uptime_seconds": uptime,
        "cpu_model": _cpu_model(),
        "arch": uname.machine,
        "total_ram_bytes": total_ram,
        "cpu_cores_physical": int(physical),
        "cpu_cores_logical": int(logical),
    }


def cpu_per_core(interval: float = 0.0) -> list[dict[str, Any]]:
    """Per-CPU utilization. Pass ``interval>0`` for a blocking measurement
    window; otherwise the value is computed against the previous call."""
    try:
        percents = psutil.cpu_percent(interval=interval if interval and interval > 0 else None, percpu=True)
    except Exception:
        percents = []
    freqs: list[float | None] = []
    try:
        per = psutil.cpu_freq(percpu=True) or []
        if isinstance(per, list):
            freqs = [float(f.current) if f and getattr(f, "current", None) is not None else None for f in per]
    except (NotImplementedError, AttributeError, OSError):
        freqs = []

    out: list[dict[str, Any]] = []
    for i, pct in enumerate(percents):
        f = freqs[i] if i < len(freqs) else None
        out.append({
            "core": i,
            "percent": float(round(pct, 1)),
            "freq_mhz": float(round(f, 0)) if f is not None else None,
        })
    return out


def disk_io_per_disk() -> list[dict[str, Any]]:
    """Per-disk MB/s + IOPS computed against the previous call's counters."""
    try:
        counters = psutil.disk_io_counters(perdisk=True) or {}
    except Exception:
        return []

    now = time.time()
    out: list[dict[str, Any]] = []

    with _disk_lock:
        for name, c in counters.items():
            prev = _disk_prev.get(name)
            _disk_prev[name] = (now, c)
            if not prev:
                continue
            prev_ts, prev_c = prev
            dt = max(0.001, now - prev_ts)
            rd_b = max(0, int(c.read_bytes) - int(prev_c.read_bytes))
            wr_b = max(0, int(c.write_bytes) - int(prev_c.write_bytes))
            rd_n = max(0, int(c.read_count) - int(prev_c.read_count))
            wr_n = max(0, int(c.write_count) - int(prev_c.write_count))
            busy_pct: float | None = None
            try:
                # psutil exposes busy_time when the kernel does (Linux >=2.6).
                if hasattr(c, "busy_time") and hasattr(prev_c, "busy_time"):
                    busy_ms = max(0, int(c.busy_time) - int(prev_c.busy_time))
                    busy_pct = float(min(100.0, (busy_ms / 1000.0 / dt) * 100.0))
            except Exception:
                busy_pct = None
            out.append({
                "name": name,
                "read_mb_s": round(rd_b / dt / (1024 * 1024), 3),
                "write_mb_s": round(wr_b / dt / (1024 * 1024), 3),
                "read_iops": round(rd_n / dt, 1),
                "write_iops": round(wr_n / dt, 1),
                "busy_percent": (round(busy_pct, 1) if busy_pct is not None else None),
            })
    return out


def _is_virtual_iface(name: str) -> bool:
    return any(name == p or name.startswith(p) for p in _VIRTUAL_IFACE_PREFIXES)


def net_per_iface(include_virtual: bool = False) -> list[dict[str, Any]]:
    """Per-interface byte/packet/error/drop rates."""
    try:
        counters = psutil.net_io_counters(pernic=True) or {}
    except Exception:
        return []

    now = time.time()
    out: list[dict[str, Any]] = []

    with _net_lock:
        for name, c in counters.items():
            if not include_virtual and _is_virtual_iface(name):
                # Track previous samples regardless so toggling include_virtual
                # later still yields a meaningful first delta.
                _net_prev[name] = (now, c)
                continue
            prev = _net_prev.get(name)
            _net_prev[name] = (now, c)
            if not prev:
                continue
            prev_ts, prev_c = prev
            dt = max(0.001, now - prev_ts)
            recv_b = max(0, int(c.bytes_recv) - int(prev_c.bytes_recv))
            sent_b = max(0, int(c.bytes_sent) - int(prev_c.bytes_sent))
            recv_p = max(0, int(c.packets_recv) - int(prev_c.packets_recv))
            sent_p = max(0, int(c.packets_sent) - int(prev_c.packets_sent))
            err_in = max(0, int(c.errin) - int(prev_c.errin))
            err_out = max(0, int(c.errout) - int(prev_c.errout))
            drop_in = max(0, int(c.dropin) - int(prev_c.dropin))
            drop_out = max(0, int(c.dropout) - int(prev_c.dropout))
            out.append({
                "name": name,
                "bytes_recv_per_sec": round(recv_b / dt, 1),
                "bytes_sent_per_sec": round(sent_b / dt, 1),
                "packets_recv_per_sec": round(recv_p / dt, 1),
                "packets_sent_per_sec": round(sent_p / dt, 1),
                "errors_in": err_in,
                "errors_out": err_out,
                "drops_in": drop_in,
                "drops_out": drop_out,
                "is_virtual": _is_virtual_iface(name),
            })
    out.sort(key=lambda r: r["bytes_recv_per_sec"] + r["bytes_sent_per_sec"], reverse=True)
    return out


def sensors() -> list[dict[str, Any]]:
    """Return a flat list of sensor readings (temps, fans, battery)."""
    out: list[dict[str, Any]] = []

    temps_fn = getattr(psutil, "sensors_temperatures", None)
    if temps_fn is not None:
        try:
            temps = temps_fn() or {}
        except Exception:
            temps = {}
        for chip, entries in temps.items():
            for e in entries or []:
                out.append({
                    "kind": "temperature",
                    "chip": chip,
                    "label": getattr(e, "label", "") or chip,
                    "current": float(getattr(e, "current", 0.0) or 0.0),
                    "high": (float(e.high) if getattr(e, "high", None) is not None else None),
                    "critical": (float(e.critical) if getattr(e, "critical", None) is not None else None),
                    "unit": "C",
                })

    fans_fn = getattr(psutil, "sensors_fans", None)
    if fans_fn is not None:
        try:
            fans = fans_fn() or {}
        except Exception:
            fans = {}
        for chip, entries in fans.items():
            for e in entries or []:
                out.append({
                    "kind": "fan",
                    "chip": chip,
                    "label": getattr(e, "label", "") or chip,
                    "current": float(getattr(e, "current", 0.0) or 0.0),
                    "high": None,
                    "critical": None,
                    "unit": "RPM",
                })

    battery_fn = getattr(psutil, "sensors_battery", None)
    if battery_fn is not None:
        try:
            b = battery_fn()
        except Exception:
            b = None
        if b is not None:
            out.append({
                "kind": "battery",
                "chip": "battery",
                "label": "battery",
                "current": float(getattr(b, "percent", 0.0) or 0.0),
                "high": None,
                "critical": None,
                "unit": "%",
                "secsleft": (int(b.secsleft) if isinstance(getattr(b, "secsleft", None), int) else None),
                "power_plugged": bool(getattr(b, "power_plugged", False)),
            })

    return out


_MOD_LINE_RE = re.compile(r"^(?P<name>[A-Za-z0-9_]+)\s+(?P<size>\d+)\s+(?P<used>\d+)")


def kernel_modules() -> list[dict[str, Any]]:
    """Parsed /proc/modules entries — first 200 rows."""
    text = _read_text_safe(_host_path("proc", "modules"))
    if not text:
        return []
    out: list[dict[str, Any]] = []
    for raw in text.splitlines():
        m = _MOD_LINE_RE.match(raw)
        if not m:
            continue
        out.append({
            "name": m.group("name"),
            "size": int(m.group("size")),
            "used_count": int(m.group("used")),
        })
        if len(out) >= 200:
            break
    return out


def _addr_text(addr: Any) -> str:
    """Format psutil's ``addr`` namedtuple/tuple as ``host:port``."""
    if not addr:
        return ""
    ip = getattr(addr, "ip", None) or (addr[0] if isinstance(addr, (tuple, list)) and addr else "")
    port = getattr(addr, "port", None)
    if port is None and isinstance(addr, (tuple, list)) and len(addr) >= 2:
        port = addr[1]
    return f"{ip or ''}:{port if port is not None else ''}"


def _proc_name(pid: int | None) -> str:
    if not pid:
        return ""
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
        return ""


def listening_ports() -> list[dict[str, Any]]:
    """All inet sockets currently in LISTEN state."""
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError, RuntimeError):
        return []

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for c in conns:
        if (c.status or "").upper() != "LISTEN":
            continue
        family = "tcp" if c.type == 1 else ("udp" if c.type == 2 else "?")
        # AF_INET6 = 10 on Linux. Tag the family so the UI can show v4/v6.
        try:
            family += "6" if int(c.family) == 10 else "4"
        except Exception:
            pass
        laddr = _addr_text(c.laddr)
        key = (laddr, c.pid, c.type)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "laddr": laddr,
            "proto": family,
            "pid": int(c.pid) if c.pid else None,
            "process": _proc_name(c.pid),
        })
    out.sort(key=lambda r: (r["laddr"], r["proto"]))
    return out

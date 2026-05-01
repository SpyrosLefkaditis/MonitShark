"""System metrics via psutil. Snapshot + rolling 60-sample buffer.

`push()` is called from a 1Hz background task started in main.py; the buffer
hands `history()` a quick rendering source for the dashboard sparklines.
"""
from __future__ import annotations

import os
import time
from collections import deque
from typing import Iterable

import psutil

from app.schemas import (
    CpuMetric,
    DiskMetric,
    MemoryMetric,
    MetricsSnapshot,
    NetMetric,
    ProcessItem,
)

_BUFFER_MAX = 60
_buffer: deque[MetricsSnapshot] = deque(maxlen=_BUFFER_MAX)

_DISK_SKIP_PREFIXES: tuple[str, ...] = (
    "/host/proc",
    "/host/sys",
    "/host/dev",
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/var/lib/docker",
    "/host/var/lib/docker",
    "/snap",
)
_DISK_SKIP_DEVICE_PREFIXES: tuple[str, ...] = ("/dev/loop",)
_DISK_MAX = 8

_PROC_TOP_N = 20

# Seed cpu_percent so the first real read is meaningful (psutil requirement).
psutil.cpu_percent(interval=None)


def _loadavg() -> tuple[float, float, float]:
    """Return (1m, 5m, 15m) load average; zeros on platforms that lack it."""
    try:
        return os.getloadavg()
    except (OSError, AttributeError):
        return (0.0, 0.0, 0.0)


def _cpu() -> CpuMetric:
    """Sample CPU + load."""
    one, five, fifteen = _loadavg()
    return CpuMetric(
        percent=float(psutil.cpu_percent(interval=None)),
        count=int(psutil.cpu_count(logical=True) or 0),
        load_1=float(one),
        load_5=float(five),
        load_15=float(fifteen),
    )


def _memory() -> MemoryMetric:
    """Sample virtual memory."""
    vm = psutil.virtual_memory()
    return MemoryMetric(
        total=int(vm.total),
        used=int(vm.used),
        available=int(vm.available),
        percent=float(vm.percent),
    )


def _disks() -> list[DiskMetric]:
    """Sample real filesystems, skipping pseudo + container overlay mounts."""
    out: list[DiskMetric] = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        mp = part.mountpoint or ""
        dev = part.device or ""
        if not mp or mp in seen:
            continue
        if any(mp.startswith(p) for p in _DISK_SKIP_PREFIXES):
            continue
        if any(dev.startswith(p) for p in _DISK_SKIP_DEVICE_PREFIXES):
            continue
        try:
            usage = psutil.disk_usage(mp)
        except (PermissionError, OSError):
            continue
        seen.add(mp)
        out.append(DiskMetric(
            mountpoint=mp,
            total=int(usage.total),
            used=int(usage.used),
            free=int(usage.free),
            percent=float(usage.percent),
        ))
        if len(out) >= _DISK_MAX:
            break
    return out


def _net() -> NetMetric:
    """Sample aggregate network counters."""
    n = psutil.net_io_counters()
    return NetMetric(
        bytes_sent=int(n.bytes_sent),
        bytes_recv=int(n.bytes_recv),
        packets_sent=int(n.packets_sent),
        packets_recv=int(n.packets_recv),
    )


def _iter_processes() -> Iterable[psutil.Process]:
    return psutil.process_iter(
        attrs=["pid", "name", "username", "cpu_percent", "memory_percent",
               "memory_info", "cmdline"],
    )


def _top_processes() -> list[ProcessItem]:
    """Return the top N processes by recent CPU%, sampled with a brief window."""
    procs = list(_iter_processes())
    # Seed cpu_percent on each Process so the next read returns a real delta.
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Short sample window so the snapshot stays sub-200ms.
    time.sleep(0.1)

    items: list[ProcessItem] = []
    for p in procs:
        try:
            info = p.info
            cpu = float(p.cpu_percent(interval=None))
            mem_info = info.get("memory_info")
            rss = int(mem_info.rss) if mem_info else 0
            cmdline_list = info.get("cmdline") or []
            cmdline = " ".join(cmdline_list) if isinstance(cmdline_list, list) else ""
            items.append(ProcessItem(
                pid=int(info.get("pid") or 0),
                name=str(info.get("name") or ""),
                user=info.get("username"),
                cpu_percent=cpu,
                mem_percent=float(info.get("memory_percent") or 0.0),
                rss=rss,
                cmdline=cmdline[:512],
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    items.sort(key=lambda x: x.cpu_percent, reverse=True)
    return items[:_PROC_TOP_N]


def snapshot() -> MetricsSnapshot:
    """Build a fresh metrics snapshot for right now."""
    return MetricsSnapshot(
        ts=time.time(),
        cpu=_cpu(),
        memory=_memory(),
        disks=_disks(),
        net=_net(),
        top_processes=_top_processes(),
    )


def push() -> MetricsSnapshot:
    """Append a fresh snapshot to the rolling buffer and return it."""
    snap = snapshot()
    _buffer.append(snap)
    return snap


def history(limit: int = 60) -> list[MetricsSnapshot]:
    """Return up to `limit` most-recent snapshots, oldest-first."""
    if limit <= 0:
        return []
    if limit >= len(_buffer):
        return list(_buffer)
    return list(_buffer)[-limit:]

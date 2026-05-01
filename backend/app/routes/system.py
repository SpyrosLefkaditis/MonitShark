"""Extended system stats — host info, per-core CPU, per-disk I/O, per-NIC
throughput, sensors, kernel modules, listening ports."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app import system_stats as ss
from app.auth import User, get_current_user

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info")
async def get_host_info(
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Kernel/distro/hostname + uptime + CPU model + RAM + core counts."""
    return ss.host_info()


@router.get("/cpu-per-core")
async def get_cpu_per_core(
    _user: Annotated[User, Depends(get_current_user)],
    interval: float = Query(0.0, ge=0.0, le=2.0),
) -> list[dict]:
    """Per-core CPU% + frequency. ``interval`` is the optional blocking
    sample window in seconds (0 = compute against previous call)."""
    return ss.cpu_per_core(interval=interval)


@router.get("/disk-io")
async def get_disk_io(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Per-disk read/write MB/s + IOPS + busy% (deltas vs previous call)."""
    return ss.disk_io_per_disk()


@router.get("/net-per-iface")
async def get_net_per_iface(
    _user: Annotated[User, Depends(get_current_user)],
    include_virtual: bool = Query(False),
) -> list[dict]:
    """Per-interface throughput. Loopback + container interfaces excluded
    unless ``include_virtual=true``."""
    return ss.net_per_iface(include_virtual=include_virtual)


@router.get("/sensors")
async def get_sensors(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Temperature/fan/battery sensors (empty list when none available)."""
    return ss.sensors()


@router.get("/kernel-modules")
async def get_kernel_modules(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Loaded kernel modules (capped at 200 rows)."""
    return ss.kernel_modules()


@router.get("/listening")
async def get_listening_ports(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """All TCP/UDP sockets in LISTEN state with owning PID + process name."""
    return ss.listening_ports()

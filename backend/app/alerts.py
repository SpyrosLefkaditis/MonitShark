"""Threshold-based alert engine + persistence.

A lifespan task (`poller_task`) runs every 10 seconds, takes the latest
metrics snapshot, and feeds it to `evaluate`. `evaluate` updates an
in-memory streak map: when a rule has been over its threshold for >=60s
continuously, we emit a single alert and mark the rule as "alerted" so
it does not re-fire until it crosses back below threshold.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app import metrics
from app.db import db
from app.schemas import Alert, AlertKind, MetricsSnapshot, Severity

log = logging.getLogger("beacon.alerts")

# Thresholds (percent).
CPU_PCT_HIGH = 90.0     # sustained 60s
MEM_PCT_HIGH = 90.0     # sustained 60s
DISK_PCT_HIGH = 90.0    # any partition

# Time a rule must remain over threshold before firing.
_SUSTAIN_S = 60.0
# Sentinel value placed in `_streaks` after we have already fired an alert
# for a rule, so we don't re-fire while still over threshold. The streak is
# cleared when the value drops back below threshold.
_ALERTED = float("inf")

# Maps a rule_key -> timestamp when the rule first crossed threshold,
# or _ALERTED if we already emitted an alert for this streak.
_streaks: dict[str, float] = {}

# Poll interval for the lifespan task.
_POLL_INTERVAL_S = 10.0


def _rule_key_disk(mountpoint: str) -> str:
    return f"disk:{mountpoint}"


async def _persist_alert(
    kind: AlertKind, severity: Severity, title: str, body: str
) -> Alert:
    """Insert a new alert row and return the persisted Alert."""
    created_at = time.time()
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO alerts (kind, severity, title, body, created_at, acknowledged_at)"
            " VALUES (?, ?, ?, ?, ?, NULL)",
            (kind, severity, title, body, created_at),
        )
        alert_id = cur.lastrowid
    return Alert(
        id=int(alert_id or 0),
        kind=kind,
        severity=severity,
        title=title,
        body=body,
        created_at=created_at,
        acknowledged_at=None,
    )


async def _update_streak(
    rule_key: str,
    over_threshold: bool,
    now: float,
    *,
    severity: Severity,
    title: str,
    body: str,
) -> None:
    """Drive the per-rule state machine and emit an alert if sustained."""
    if not over_threshold:
        # Below threshold: reset streak so a new crossing can fire later.
        _streaks.pop(rule_key, None)
        return

    started = _streaks.get(rule_key)
    if started is None:
        _streaks[rule_key] = now
        return
    if started == _ALERTED:
        # Already fired this streak; wait for it to clear.
        return
    if now - started >= _SUSTAIN_S:
        await _persist_alert("threshold", severity, title, body)
        _streaks[rule_key] = _ALERTED


async def evaluate(snapshot: MetricsSnapshot) -> None:
    """Apply threshold rules to a snapshot and emit alerts as needed."""
    now = snapshot.ts or time.time()

    cpu_pct = snapshot.cpu.percent
    await _update_streak(
        "cpu",
        cpu_pct >= CPU_PCT_HIGH,
        now,
        severity="high",
        title=f"CPU usage above {CPU_PCT_HIGH:.0f}% for 60s",
        body=f"CPU usage sustained at {cpu_pct:.1f}% (load1={snapshot.cpu.load_1:.2f}).",
    )

    mem_pct = snapshot.memory.percent
    await _update_streak(
        "memory",
        mem_pct >= MEM_PCT_HIGH,
        now,
        severity="high",
        title=f"Memory usage above {MEM_PCT_HIGH:.0f}% for 60s",
        body=f"Memory usage sustained at {mem_pct:.1f}% (used {snapshot.memory.used} of {snapshot.memory.total}).",
    )

    # Per-partition disk: any partition over threshold fires a single alert
    # per partition. Disk alerts fire on first detection (no sustain window).
    seen_disks: set[str] = set()
    for disk in snapshot.disks:
        key = _rule_key_disk(disk.mountpoint)
        seen_disks.add(key)
        if disk.percent >= DISK_PCT_HIGH:
            if _streaks.get(key) == _ALERTED:
                continue
            await _persist_alert(
                "threshold",
                "high",
                f"Disk usage above {DISK_PCT_HIGH:.0f}% on {disk.mountpoint}",
                f"Filesystem at {disk.mountpoint} is {disk.percent:.1f}% full "
                f"(used {disk.used} of {disk.total}).",
            )
            _streaks[key] = _ALERTED
        else:
            _streaks.pop(key, None)

    # Clear streaks for partitions that disappeared from the snapshot.
    for key in [k for k in _streaks if k.startswith("disk:") and k not in seen_disks]:
        _streaks.pop(key, None)


async def alert_finding(
    finding_id: str, severity: Severity, title: str, body: str
) -> Alert:
    """Wrapper for findings audits to raise a finding-kind alert."""
    composed = f"[finding:{finding_id}] {body}"
    return await _persist_alert("finding", severity, title, composed)


def _row_to_alert(row: tuple[Any, ...]) -> Alert:
    return Alert(
        id=int(row[0]),
        kind=row[1],
        severity=row[2],
        title=row[3],
        body=row[4],
        created_at=float(row[5]),
        acknowledged_at=float(row[6]) if row[6] is not None else None,
    )


async def list_alerts(status: str | None = None) -> list[Alert]:
    """Return alerts. Default: unacked first by created_at desc; "all" returns everything."""
    if status == "all":
        rows = await db.fetchall(
            "SELECT id, kind, severity, title, body, created_at, acknowledged_at"
            " FROM alerts ORDER BY created_at DESC"
        )
    else:
        # Default behaviour ("open" or None): only unacknowledged alerts.
        rows = await db.fetchall(
            "SELECT id, kind, severity, title, body, created_at, acknowledged_at"
            " FROM alerts WHERE acknowledged_at IS NULL ORDER BY created_at DESC"
        )
    return [_row_to_alert(r) for r in rows]


async def acknowledge(alert_id: int) -> bool:
    """Mark an alert acknowledged. Returns True iff the row existed and was unacked."""
    now = time.time()
    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE alerts SET acknowledged_at = ?"
            " WHERE id = ? AND acknowledged_at IS NULL",
            (now, alert_id),
        )
        affected = cur.rowcount or 0
    return affected > 0


async def poller_task() -> None:
    """Forever-running task: every 10s evaluate the latest snapshot."""
    while True:
        try:
            history = metrics.history(1)
            snap = history[-1] if history else metrics.snapshot()
            await evaluate(snap)
        except asyncio.CancelledError:
            raise
        except Exception:  # never let the task die  # noqa: BLE001
            log.exception("alert poller iteration failed")
        try:
            await asyncio.sleep(_POLL_INTERVAL_S)
        except asyncio.CancelledError:
            raise

"""Cron read/write via python-crontab on /host crontabs.

We always pass `tabfile=...` to `CronTab(...)` so the lib reads/writes the file
directly instead of shelling out to `crontab -l`/`crontab -` (which would not
hit the host's spool through the bind-mount).

Entry IDs are synthesized as f"{user}::{idx}" where idx is the entry's position
in that user's crontab (0-based). IDs are NOT stable across edits — the caller
re-fetches after each mutation.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from crontab import CronTab

from app.schemas import (
    CronCreateIn,
    CronEntry,
    CronRunIn,
    CronRunOut,
    CronUpdateIn,
)
from app.util.paths import resolve_safe
from app.util.sh import run

_USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_ID_RE = re.compile(r"^([a-z_][a-z0-9_-]{0,31})::(\d+)$")

_SPOOL_ROOT = Path("/host/var/spool/cron")
_SYSTEM_CRONTAB = Path("/host/etc/crontab")
_SYSTEM_USER = "_system"  # synthetic user label for /etc/crontab entries


class CronError(ValueError):
    """Cron operation rejected (bad user, bad id, parse failure)."""


def _validate_user(user: str) -> None:
    if not _USER_RE.match(user):
        raise CronError(f"invalid username: {user!r}")


def _parse_id(entry_id: str) -> tuple[str, int]:
    m = _ID_RE.match(entry_id)
    if not m:
        raise CronError(f"invalid cron id: {entry_id!r}")
    return m.group(1), int(m.group(2))


def _tabfile_for(user: str) -> Path:
    """Return the on-disk crontab path for a user, validated against the allowlist."""
    if user == _SYSTEM_USER:
        return resolve_safe(_SYSTEM_CRONTAB, [_SYSTEM_CRONTAB.parent])
    _validate_user(user)
    return resolve_safe(_SPOOL_ROOT / user, [_SPOOL_ROOT])


def _open_user(user: str) -> CronTab:
    """Open a user's crontab via tabfile, never via the `crontab` binary."""
    tabfile = _tabfile_for(user)
    if user == _SYSTEM_USER:
        # /etc/crontab has a user field per line — treat as system-wide tab.
        return CronTab(tabfile=str(tabfile), user=False)
    return CronTab(user=user, tabfile=str(tabfile))


def _entry_to_model(user: str, idx: int, entry) -> CronEntry:
    return CronEntry(
        id=f"{user}::{idx}",
        user=user,
        schedule=str(entry.slices),
        command=str(entry.command),
        comment=entry.comment or None,
        enabled=bool(entry.is_enabled()),
    )


def _list_one(user: str) -> list[CronEntry]:
    tabfile = _tabfile_for(user)
    if not tabfile.exists():
        return []
    cron = _open_user(user)
    return [_entry_to_model(user, idx, e) for idx, e in enumerate(cron)]


def list_all(user: str | None = None) -> list[CronEntry]:
    """List crontab entries across users (or just one if `user` is given)."""
    if user is not None:
        if user == _SYSTEM_USER:
            return _list_one(_SYSTEM_USER)
        _validate_user(user)
        return _list_one(user)

    out: list[CronEntry] = []
    if _SPOOL_ROOT.exists():
        try:
            names = sorted(os.listdir(_SPOOL_ROOT))
        except OSError:
            names = []
        for name in names:
            if not _USER_RE.match(name):
                continue
            try:
                out.extend(_list_one(name))
            except (CronError, OSError):
                # Per-user failure shouldn't poison the whole list.
                continue
    if _SYSTEM_CRONTAB.exists():
        try:
            out.extend(_list_one(_SYSTEM_USER))
        except (CronError, OSError):
            pass
    return out


def create(payload: CronCreateIn) -> CronEntry:
    """Append a new entry to the user's crontab."""
    _validate_user(payload.user)
    tabfile = _tabfile_for(payload.user)
    tabfile.parent.mkdir(parents=True, exist_ok=True)
    if not tabfile.exists():
        tabfile.touch(mode=0o600)
    cron = _open_user(payload.user)
    job = cron.new(command=payload.command, comment=payload.comment or "")
    # python-crontab raises on invalid schedule via setall().
    job.setall(payload.schedule)
    cron.write()
    # Reload to get the persisted index for ID synthesis.
    refreshed = list(_open_user(payload.user))
    idx = len(refreshed) - 1 if refreshed else 0
    return _entry_to_model(payload.user, idx, refreshed[idx])


def delete(entry_id: str) -> bool:
    """Remove the entry at idx from `user`'s crontab. Returns True if removed."""
    user, idx = _parse_id(entry_id)
    if user != _SYSTEM_USER:
        _validate_user(user)
    cron = _open_user(user)
    entries = list(cron)
    if idx < 0 or idx >= len(entries):
        raise CronError(f"index {idx} out of range for user {user!r}")
    cron.remove(entries[idx])
    cron.write()
    return True


def update(entry_id: str, patch: CronUpdateIn) -> CronEntry:
    """Patch fields on the entry at idx and persist."""
    user, idx = _parse_id(entry_id)
    if user != _SYSTEM_USER:
        _validate_user(user)
    cron = _open_user(user)
    entries = list(cron)
    if idx < 0 or idx >= len(entries):
        raise CronError(f"index {idx} out of range for user {user!r}")
    entry = entries[idx]
    if patch.schedule is not None:
        entry.setall(patch.schedule)
    if patch.command is not None:
        entry.set_command(patch.command)
    if patch.comment is not None:
        entry.set_comment(patch.comment)
    if patch.enabled is not None:
        entry.enable(patch.enabled)
    cron.write()
    refreshed = list(_open_user(user))
    return _entry_to_model(user, idx, refreshed[idx])


def run_script(payload: CronRunIn) -> CronRunOut:
    """Execute an allowlisted script (under /opt/cockpit/scripts) ad hoc."""
    # resolve_safe enforces the script lives under /opt/cockpit/scripts.
    script = resolve_safe(payload.command, [Path("/opt/cockpit/scripts")])
    cmd = [str(script), *payload.args]
    timeout = max(1, min(int(payload.timeout_s), 300))
    result = run(cmd, timeout=timeout)
    return CronRunOut(rc=result.returncode, stdout=result.stdout, stderr=result.stderr)

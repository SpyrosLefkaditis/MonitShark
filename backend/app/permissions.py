"""Inspect & modify Linux file permissions on the host.

Curated browseable roots only — never a generic file browser.

list_dir / get_file_info read attributes via os.stat. uid/gid are translated
to names by parsing /host/etc/passwd and /host/etc/group, NOT by calling pwd
or grp (those resolve against the container's NSS databases, not the host's).

chmod_path uses os.chmod (the backend container runs as root with /host
mounted rw). chown_path goes through `nsenter -- chown` so the host's NSS
resolves the names.
"""
from __future__ import annotations

import os
import re
import stat as stat_mod
import time
from pathlib import Path
from typing import Any

from app.util.nsenter import nsenter
from app.util.paths import HOST_ROOT, resolve_safe
from app.util.sh import CommandRejected, run

BROWSEABLE_ROOTS: list[Path] = [
    HOST_ROOT / "etc",
    HOST_ROOT / "opt" / "cockpit",
    HOST_ROOT / "var" / "log",
    HOST_ROOT / "home",
    HOST_ROOT / "root",
]

_HOST_PREFIX = str(HOST_ROOT)
_MAX_ENTRIES = 500
_MODE_RE = re.compile(r"^[0-7]{3,4}$")
_NAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}\$?$")

_PASSWD_FILE = HOST_ROOT / "etc" / "passwd"
_GROUP_FILE = HOST_ROOT / "etc" / "group"
_PASSWD_CACHE: tuple[float, dict[int, str]] | None = None
_GROUP_CACHE: tuple[float, dict[int, str]] | None = None
_NSS_TTL_S = 30.0


def _load_nss(path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        try:
            uid = int(parts[2])
        except ValueError:
            continue
        out[uid] = parts[0]
    return out


def _uid_map() -> dict[int, str]:
    global _PASSWD_CACHE
    now = time.time()
    if _PASSWD_CACHE and now - _PASSWD_CACHE[0] < _NSS_TTL_S:
        return _PASSWD_CACHE[1]
    data = _load_nss(_PASSWD_FILE)
    _PASSWD_CACHE = (now, data)
    return data


def _gid_map() -> dict[int, str]:
    global _GROUP_CACHE
    now = time.time()
    if _GROUP_CACHE and now - _GROUP_CACHE[0] < _NSS_TTL_S:
        return _GROUP_CACHE[1]
    data = _load_nss(_GROUP_FILE)
    _GROUP_CACHE = (now, data)
    return data


def _to_internal(path: str | Path) -> Path:
    """Map a display path (/etc/foo) or host-prefixed path to /host/etc/foo."""
    raw = str(path).strip()
    if not raw:
        raise ValueError("empty path")
    if raw.startswith(_HOST_PREFIX):
        return Path(raw)
    if not raw.startswith("/"):
        raw = "/" + raw
    return Path(_HOST_PREFIX + raw)


def _to_display(p: Path) -> str:
    s = str(p)
    if s.startswith(_HOST_PREFIX):
        rest = s[len(_HOST_PREFIX):] or "/"
        return rest
    return s


def _entry_info(p: Path, name: str | None = None) -> dict[str, Any]:
    """Build an entry record from a path; uses lstat to avoid following symlinks."""
    st = p.lstat()
    mode = st.st_mode
    perm = stat_mod.S_IMODE(mode)
    is_dir = stat_mod.S_ISDIR(mode)
    is_link = stat_mod.S_ISLNK(mode)
    return {
        "name": name if name is not None else p.name,
        "is_dir": bool(is_dir),
        "is_link": bool(is_link),
        "mode": int(perm),
        "mode_octal": format(perm, "04o"),
        "owner": _uid_map().get(st.st_uid, str(st.st_uid)),
        "group": _gid_map().get(st.st_gid, str(st.st_gid)),
        "uid": int(st.st_uid),
        "gid": int(st.st_gid),
        "size": int(st.st_size),
        "mtime": float(st.st_mtime),
    }


def list_dir(path: str) -> dict[str, Any]:
    """List a directory under one of BROWSEABLE_ROOTS."""
    internal = _to_internal(path)
    resolved = resolve_safe(internal, BROWSEABLE_ROOTS)
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {_to_display(resolved)}")
    if not resolved.is_dir():
        raise ValueError(f"not a directory: {_to_display(resolved)}")
    try:
        names = sorted(os.listdir(resolved))
    except OSError as e:
        raise ValueError(f"cannot list directory: {e}") from e

    entries: list[dict[str, Any]] = []
    for name in names[:_MAX_ENTRIES]:
        child = resolved / name
        try:
            entries.append(_entry_info(child, name=name))
        except OSError:
            # Permission denied / vanished entries shouldn't break the listing.
            continue
    truncated = len(names) > _MAX_ENTRIES
    return {
        "path": _to_display(resolved),
        "entries": entries,
        "total": len(names),
        "truncated": truncated,
    }


def get_file_info(path: str) -> dict[str, Any]:
    """Return one entry's metadata."""
    internal = _to_internal(path)
    resolved = resolve_safe(internal, BROWSEABLE_ROOTS)
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {_to_display(resolved)}")
    info = _entry_info(resolved)
    info["path"] = _to_display(resolved)
    return info


def chmod_path(path: str, mode_octal: str) -> dict[str, Any]:
    """Set permissions on a file or directory using os.chmod."""
    if not isinstance(mode_octal, str) or not _MODE_RE.match(mode_octal):
        raise ValueError(f"invalid octal mode: {mode_octal!r}")
    internal = _to_internal(path)
    resolved = resolve_safe(internal, BROWSEABLE_ROOTS)
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {_to_display(resolved)}")
    new_mode = int(mode_octal, 8)
    os.chmod(resolved, new_mode)
    info = _entry_info(resolved)
    info["path"] = _to_display(resolved)
    return info


def chown_path(
    path: str,
    owner: str | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    """Change ownership using `nsenter -- chown owner:group <path>`.

    Either owner or group may be omitted (passed as None).
    """
    if owner is None and group is None:
        raise ValueError("at least one of owner or group is required")
    if owner is not None and not _NAME_RE.match(owner):
        raise ValueError(f"invalid owner name: {owner!r}")
    if group is not None and not _NAME_RE.match(group):
        raise ValueError(f"invalid group name: {group!r}")

    internal = _to_internal(path)
    resolved = resolve_safe(internal, BROWSEABLE_ROOTS)
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {_to_display(resolved)}")

    spec = ""
    if owner is not None:
        spec += owner
    if group is not None:
        spec += f":{group}"
    host_path = _to_display(resolved)
    cmd = nsenter(["chown", spec, host_path])
    try:
        cc = run(cmd, timeout=15)
    except CommandRejected as e:
        raise ValueError(f"chown rejected: {e}") from e
    if cc.returncode != 0:
        raise ValueError(
            f"chown failed (rc={cc.returncode}): {cc.stderr.strip() or cc.stdout.strip()}"
        )
    # Invalidate caches so the new owner/group resolve immediately.
    global _PASSWD_CACHE, _GROUP_CACHE
    _PASSWD_CACHE = None
    _GROUP_CACHE = None
    info = _entry_info(resolved)
    info["path"] = host_path
    return info


def browseable_roots() -> list[str]:
    """Return display-form roots for the UI quick-link list."""
    return [_to_display(r) for r in BROWSEABLE_ROOTS]

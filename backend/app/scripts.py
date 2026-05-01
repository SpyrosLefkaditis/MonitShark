"""User-defined bash scripts under /opt/cockpit/scripts.

Scripts are plain text files the user creates in the UI. They can be:
  - Executed ad hoc (cap timeout 300s, validated argv).
  - Installed as a oneshot systemd unit at /etc/systemd/system/<name>.service
    on the host (does NOT enable/start automatically).
  - Scheduled via cron (root or per-user crontab) using python-crontab.

Path safety: every script name is validated against ^[a-zA-Z0-9_-]{1,64}$ and
files always live under SCRIPTS_DIR via resolve_safe — arbitrary host paths
never reach disk.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from crontab import CronSlices, CronTab

from app.util.nsenter import nsenter
from app.util.paths import resolve_safe
from app.util.sh import CommandRejected, run

SCRIPTS_DIR = Path("/host/opt/cockpit/scripts")
SCRIPTS_ROOTS = [SCRIPTS_DIR]

_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
_USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_ARG_RE = re.compile(r"^[a-zA-Z0-9_./=:,@+-]+$")
_RESTART_VALUES: frozenset[str] = frozenset({"no", "always", "on-failure", "on-abnormal"})

_MAX_CONTENT_BYTES = 1024 * 1024  # 1 MiB
_MAX_TIMEOUT_S = 300
_SYSTEMD_DIR = Path("/host/etc/systemd/system")
_CRON_SPOOL = Path("/host/var/spool/cron")


class ScriptError(ValueError):
    """Script operation rejected (bad name, oversized, missing, etc.)."""


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ScriptError(f"invalid script name: {name!r}")
    return name


def _path_for(name: str) -> Path:
    _validate_name(name)
    return resolve_safe(SCRIPTS_DIR / f"{name}.sh", SCRIPTS_ROOTS)


def _ensure_dir() -> None:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def _meta(p: Path) -> dict[str, Any]:
    st = p.stat()
    return {
        "name": p.stem,
        "size_bytes": int(st.st_size),
        "modified_at": float(st.st_mtime),
        "executable": bool(st.st_mode & 0o111),
    }


def list_scripts() -> list[dict[str, Any]]:
    """Return metadata for every *.sh script under SCRIPTS_DIR."""
    _ensure_dir()
    out: list[dict[str, Any]] = []
    try:
        names = sorted(os.listdir(SCRIPTS_DIR))
    except OSError:
        return []
    for fname in names:
        if not fname.endswith(".sh"):
            continue
        stem = fname[:-3]
        if not _NAME_RE.match(stem):
            continue
        p = SCRIPTS_DIR / fname
        if not p.is_file():
            continue
        try:
            out.append(_meta(p))
        except OSError:
            continue
    return out


def get_script(name: str) -> dict[str, Any]:
    """Return the script content + modified timestamp."""
    p = _path_for(name)
    if not p.exists() or not p.is_file():
        raise ScriptError(f"script not found: {name!r}")
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ScriptError(f"cannot read script: {e}") from e
    return {
        "name": p.stem,
        "content": content,
        "modified_at": float(p.stat().st_mtime),
    }


def save_script(name: str, content: str, make_executable: bool = True) -> dict[str, Any]:
    """Create or overwrite a script under SCRIPTS_DIR."""
    if not isinstance(content, str):
        raise ScriptError("content must be a string")
    if len(content.encode("utf-8")) > _MAX_CONTENT_BYTES:
        raise ScriptError(f"content exceeds {_MAX_CONTENT_BYTES} bytes")
    _ensure_dir()
    p = _path_for(name)
    p.write_text(content, encoding="utf-8")
    mode = 0o755 if make_executable else 0o644
    os.chmod(p, mode)
    return _meta(p)


def delete_script(name: str) -> dict[str, Any]:
    """Remove the script file."""
    p = _path_for(name)
    if not p.exists():
        raise ScriptError(f"script not found: {name!r}")
    p.unlink()
    return {"name": name, "deleted": True}


def _validate_args(args: list[str]) -> list[str]:
    if not isinstance(args, list):
        raise ScriptError("args must be a list of strings")
    out: list[str] = []
    for i, a in enumerate(args):
        if not isinstance(a, str):
            raise ScriptError(f"args[{i}] must be a string")
        if not _ARG_RE.match(a):
            raise ScriptError(f"args[{i}] contains disallowed characters: {a!r}")
        out.append(a)
    return out


def run_script(
    name: str,
    args: list[str] | None = None,
    timeout_s: int = 60,
) -> dict[str, Any]:
    """Execute a script ad hoc and return rc/stdout/stderr."""
    p = _path_for(name)
    if not p.exists() or not p.is_file():
        raise ScriptError(f"script not found: {name!r}")
    if not (p.stat().st_mode & 0o111):
        raise ScriptError(f"script is not executable: {name!r}")
    safe_args = _validate_args(list(args or []))
    timeout = max(1, min(int(timeout_s), _MAX_TIMEOUT_S))
    try:
        cc = run([str(p), *safe_args], timeout=timeout)
    except CommandRejected as e:
        raise ScriptError(f"command rejected: {e}") from e
    return {
        "name": name,
        "rc": cc.returncode,
        "stdout": cc.stdout,
        "stderr": cc.stderr,
        "timeout_s": timeout,
    }


def _validate_service_name(service_name: str) -> str:
    if not isinstance(service_name, str) or not _SERVICE_NAME_RE.match(service_name):
        raise ScriptError(f"invalid service name: {service_name!r}")
    if service_name.endswith(".service"):
        service_name = service_name[: -len(".service")]
        if not _SERVICE_NAME_RE.match(service_name):
            raise ScriptError(f"invalid service name: {service_name!r}")
    return service_name


def install_as_service(
    script_name: str,
    service_name: str,
    description: str = "",
    restart: str = "no",
) -> dict[str, Any]:
    """Write a oneshot systemd unit file for a script and reload daemon.

    Does NOT enable or start the service — caller should use the Services page.
    """
    _path_for(script_name)  # validates name + lives under SCRIPTS_DIR
    short = _validate_service_name(service_name)
    if restart not in _RESTART_VALUES:
        raise ScriptError(f"invalid restart policy: {restart!r}")
    if description and any(ch in description for ch in "\n\r"):
        raise ScriptError("description must not contain newlines")
    desc = description.strip() or f"Run {script_name}.sh"

    unit_path = resolve_safe(_SYSTEMD_DIR / f"{short}.service", [_SYSTEMD_DIR])
    unit_path.parent.mkdir(parents=True, exist_ok=True)

    exec_start = f"/opt/cockpit/scripts/{script_name}.sh"
    content = (
        "[Unit]\n"
        f"Description={desc}\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={exec_start}\n"
        f"Restart={restart}\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    unit_path.write_text(content, encoding="utf-8")
    os.chmod(unit_path, 0o644)

    cmd = nsenter(["systemctl", "daemon-reload"])
    try:
        cc = run(cmd, timeout=15)
    except CommandRejected as e:
        raise ScriptError(f"daemon-reload rejected: {e}") from e
    return {
        "script": script_name,
        "service": f"{short}.service",
        "unit_path": f"/etc/systemd/system/{short}.service",
        "daemon_reload_rc": cc.returncode,
        "daemon_reload_stderr": cc.stderr,
    }


def _crontab_for(user: str) -> tuple[Path, CronTab]:
    """Open a user's crontab via tabfile (no `crontab` binary)."""
    if not _USER_RE.match(user):
        raise ScriptError(f"invalid username: {user!r}")
    tabfile = resolve_safe(_CRON_SPOOL / user, [_CRON_SPOOL])
    tabfile.parent.mkdir(parents=True, exist_ok=True)
    if not tabfile.exists():
        tabfile.touch(mode=0o600)
    return tabfile, CronTab(user=user, tabfile=str(tabfile))


def schedule_via_cron(
    script_name: str,
    schedule: str,
    user: str = "root",
) -> dict[str, Any]:
    """Append a cron entry for the script in `user`'s crontab."""
    _path_for(script_name)
    if not isinstance(schedule, str) or not schedule.strip():
        raise ScriptError("schedule is required")
    schedule = schedule.strip()
    if not (schedule.startswith("@") or CronSlices.is_valid(schedule)):
        raise ScriptError(f"invalid cron schedule: {schedule!r}")

    tabfile, cron = _crontab_for(user)
    command = f"/opt/cockpit/scripts/{script_name}.sh"
    job = cron.new(command=command, comment=f"script:{script_name}")
    try:
        job.setall(schedule)
    except (ValueError, KeyError) as e:
        raise ScriptError(f"invalid cron schedule: {e}") from e
    cron.write()
    return {
        "script": script_name,
        "user": user,
        "schedule": schedule,
        "command": command,
        "tabfile": str(tabfile),
        "scheduled_at": time.time(),
    }

"""systemd unit listing + control via `nsenter -- systemctl` (always works in
this container topology). pystemd is a future perf optimization — leave a
single-line switch ready (`_BACKEND`) so we can flip it later without churn.

Names are validated against `_NAME_RE`; everything else passes through
`run()` with `trust_args=False` (the regex bound makes that safe).
"""
from __future__ import annotations

import re

from app.schemas import ServiceAction, ServiceActionOut, ServiceItem
from app.util.nsenter import nsenter
from app.util.sh import CommandRejected, run

_BACKEND = "systemctl"

_NAME_RE = re.compile(r"^[a-zA-Z0-9_@.\-:]+$")
_DASHBOARD_SUFFIX = ".service"
_SKIP_SUFFIXES: tuple[str, ...] = (".scope", ".slice", ".target", ".device", ".mount")
_VALID_ACTIONS: frozenset[str] = frozenset({"start", "stop", "restart", "reload"})


class ServiceError(RuntimeError):
    """Raised when systemctl returns non-zero or output cannot be parsed."""


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(f"invalid unit name: {name!r}")
    return name


def _systemctl(args: list[str], *, timeout: float = 15) -> tuple[int, str, str]:
    """Run `nsenter -- systemctl <args>` and return (rc, stdout, stderr)."""
    cmd = nsenter(["systemctl", *args])
    try:
        cc = run(cmd, timeout=timeout)
    except CommandRejected as e:
        raise ServiceError(f"systemctl rejected: {e}") from e
    return cc.returncode, cc.stdout, cc.stderr


def _parse_list_units(stdout: str) -> list[ServiceItem]:
    """Parse `systemctl list-units --no-legend --plain` output.

    Columns: UNIT LOAD ACTIVE SUB DESCRIPTION...
    """
    items: list[ServiceItem] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Strip leading bullet chars systemctl sometimes prepends ("●").
        if line[:1] in ("*", "●", "○"):
            line = line[1:].strip()
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        name, load_state, active_state, sub_state = parts[0], parts[1], parts[2], parts[3]
        description = parts[4] if len(parts) >= 5 else ""
        if any(name.endswith(suf) for suf in _SKIP_SUFFIXES):
            continue
        if not name.endswith(_DASHBOARD_SUFFIX):
            continue
        items.append(ServiceItem(
            name=name,
            description=description,
            load_state=load_state,
            active_state=active_state,
            sub_state=sub_state,
        ))
    return items


def list_units(state: str | None = None) -> list[ServiceItem]:
    """List `.service` units. `state` filters by `--state=` (e.g. 'active')."""
    args = ["list-units", "--type=service", "--all", "--no-legend", "--no-pager", "--plain"]
    if state:
        if not re.match(r"^[a-zA-Z\-,]+$", state):
            raise ValueError(f"invalid state filter: {state!r}")
        args.append(f"--state={state}")
    rc, out, err = _systemctl(args)
    if rc != 0 and not out:
        raise ServiceError(err.strip() or f"systemctl list-units rc={rc}")
    return _parse_list_units(out)


def _is_enabled(name: str) -> str | None:
    """Return the `is-enabled` string ('enabled', 'disabled', 'static', ...) or None."""
    rc, out, err = _systemctl(["is-enabled", name])
    text = (out or err).strip().splitlines()
    val = text[-1].strip() if text else ""
    return val or None


def _show(name: str) -> dict[str, str]:
    """Return parsed `systemctl show <name>` key=value pairs."""
    rc, out, _err = _systemctl([
        "show", name,
        "--property=Description,LoadState,ActiveState,SubState,UnitFileState",
    ])
    fields: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            fields[k.strip()] = v.strip()
    return fields


def _journal(name: str, lines: int = 50) -> list[str]:
    """Return the last `lines` of journalctl for the unit."""
    cmd = nsenter([
        "journalctl", "-u", name, "-n", str(int(lines)),
        "--no-pager", "--output=short-iso",
    ])
    try:
        cc = run(cmd, timeout=15)
    except CommandRejected:
        return []
    if not cc.ok and not cc.stdout:
        return []
    return [ln for ln in cc.stdout.splitlines() if ln.strip()]


def detail(name: str) -> dict:
    """Return a dict with name, description, states, enabled, and recent journal lines."""
    _validate_name(name)
    fields = _show(name)
    enabled = fields.get("UnitFileState") or _is_enabled(name)
    return {
        "name": name,
        "description": fields.get("Description", ""),
        "load_state": fields.get("LoadState", ""),
        "active_state": fields.get("ActiveState", ""),
        "sub_state": fields.get("SubState", ""),
        "enabled": enabled,
        "journal": _journal(name, lines=50),
    }


def action(name: str, act: ServiceAction) -> ServiceActionOut:
    """Run `systemctl <act> <name>` after validating both inputs."""
    _validate_name(name)
    if act not in _VALID_ACTIONS:
        raise ValueError(f"invalid action: {act!r}")
    rc, out, err = _systemctl([act, name], timeout=30)
    combined = (out + err).strip()
    return ServiceActionOut(ok=(rc == 0), output=combined)

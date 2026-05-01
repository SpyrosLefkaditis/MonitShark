"""Apply-fix dispatch table for audit findings.

A finding's `id` looks like `ssh.permit_root_login.<10hex>`; the prefix before
the trailing hash identifies the fix family. Each family has an idempotent
applier that knows how to mutate the host config + reload the relevant
service. New audit findings can register a fix without changing this module's
public surface — just add an entry to FIXES.

ALL fix functions return dicts of shape `{"ok": bool, "message": str}`.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.config import settings
from app.util.nsenter import nsenter
from app.util.sh import run

HOST_ROOT = Path(settings.host_root)
SSHD_CONFIG = HOST_ROOT / "etc" / "ssh" / "sshd_config"


def _set_or_replace_directive(content: str, key: str, value: str) -> str:
    """Replace `Key …` lines (case-insensitive, comment-stripped); append if absent."""
    lines = content.splitlines()
    pattern = re.compile(rf"^\s*#?\s*{re.escape(key)}\b.*$", re.IGNORECASE)
    found = False
    new_lines: list[str] = []
    for line in lines:
        if pattern.match(line):
            new_lines.append(f"{key} {value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{key} {value}")
    return "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")


def _reload_sshd() -> bool:
    """Try to reload sshd via systemctl. Returns True on success."""
    for unit in ("ssh.service", "sshd.service"):
        r = run(nsenter(["systemctl", "reload", unit]))
        if r.ok:
            return True
    return False


def _apply_ssh_directive(key: str, value: str) -> dict:
    if not SSHD_CONFIG.exists():
        return {"ok": False, "message": f"{SSHD_CONFIG} does not exist on host"}
    original = SSHD_CONFIG.read_text()
    updated = _set_or_replace_directive(original, key, value)
    if original == updated:
        return {"ok": True, "message": f"{key} already set to {value}; nothing to change"}
    # Backup then write
    backup = SSHD_CONFIG.with_suffix(SSHD_CONFIG.suffix + ".beacon.bak")
    if not backup.exists():
        backup.write_text(original)
    SSHD_CONFIG.write_text(updated)
    reloaded = _reload_sshd()
    return {
        "ok": True,
        "message": (
            f"Set `{key} {value}` in {SSHD_CONFIG}. "
            + ("sshd reloaded." if reloaded else "sshd reload skipped (service not running).")
        ),
    }


def fix_ssh_permit_root_login() -> dict:
    return _apply_ssh_directive("PermitRootLogin", "no")


def fix_ssh_password_authentication() -> dict:
    return _apply_ssh_directive("PasswordAuthentication", "no")


def fix_ssh_kbd_interactive() -> dict:
    return _apply_ssh_directive("KbdInteractiveAuthentication", "no")


def fix_ssh_permit_empty_passwords() -> dict:
    return _apply_ssh_directive("PermitEmptyPasswords", "no")


def fix_ssh_protocol_1() -> dict:
    return _apply_ssh_directive("Protocol", "2")


def fix_ssh_x11_forwarding() -> dict:
    return _apply_ssh_directive("X11Forwarding", "no")


def fix_world_writable(finding_evidence: dict) -> dict:
    """For a `permissions.world_writable_*` finding, chmod o-w on the offending path."""
    path = finding_evidence.get("path") or finding_evidence.get("file")
    if not isinstance(path, str) or not path.startswith("/"):
        return {"ok": False, "message": "no path in finding evidence"}
    target = HOST_ROOT / path.lstrip("/")
    if not target.exists():
        return {"ok": False, "message": f"path {path} no longer exists"}
    import os
    cur = target.stat().st_mode & 0o7777
    new = cur & ~0o002
    os.chmod(target, new)
    return {"ok": True, "message": f"Removed world-write from {path} (mode {oct(cur)} → {oct(new)})"}


# Map fix_id (the prefix before the trailing hash) → callable.
# Audit findings should set fix_id to one of these keys to be auto-fixable.
FIXES: dict[str, callable] = {
    "ssh.permit_root_login": fix_ssh_permit_root_login,
    "ssh.password_authentication": fix_ssh_password_authentication,
    "ssh.kbd_interactive": fix_ssh_kbd_interactive,
    "ssh.permit_empty_passwords": fix_ssh_permit_empty_passwords,
    "ssh.protocol_1": fix_ssh_protocol_1,
    "ssh.x11_forwarding": fix_ssh_x11_forwarding,
}


def apply_fix(fix_id: str | None, evidence: dict | None = None) -> dict:
    """Dispatch a fix. fix_id can be the full finding id (with hash) or just
    the family prefix. Returns {ok, message}."""
    if not fix_id:
        return {"ok": False, "message": "no fix_id"}
    # Accept either the full id (with .<hash>) or just the family.
    family = fix_id
    parts = fix_id.rsplit(".", 1)
    if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{6,40}", parts[1] or ""):
        family = parts[0]
    fn = FIXES.get(family)
    if fn is None:
        # Path-based fix (world-writable etc.)
        if family.startswith("permissions.world_writable") and evidence:
            return fix_world_writable(evidence)
        return {"ok": False, "message": f"no fix registered for {family!r}"}
    return fn()

"""Destructive @tool wrappers — every tool here is gated by the
confirmation node in `agent/graph.py`. Names listed in DESTRUCTIVE_NAMES are
the source of truth for what triggers `interrupt()` before execution.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app import services as services_mod
from app import users as users_mod
from app.fixes import apply_fix as _apply_fix
from app.audits import REGISTRY as AUDITS  # noqa: F401  (used elsewhere)


@tool
def create_user(
    username: str,
    sudo: bool = False,
    password: str | None = None,
    ssh_public_key: str | None = None,
    fullname: str | None = None,
    shell: str = "/bin/bash",
) -> dict:
    """Create a Linux user. Optionally adds them to the sudo group, sets a
    password, and installs an SSH public key into their authorized_keys.
"""
    return users_mod.create_user(
        username,
        fullname=fullname, sudo=sudo,
        password=password, ssh_public_key=ssh_public_key,
        shell=shell,
    )


@tool
def add_ssh_key(username: str, public_key: str) -> dict:
    """Append an OpenSSH public key to a user's authorized_keys (idempotent —
    no-ops if already present). REQUIRES USER CONFIRMATION."""
    return users_mod.add_ssh_key(username, public_key)


@tool
def lock_user(username: str) -> dict:
    """Lock a user account so they cannot log in (passwd -l). Reversible via
    unlock_user. REQUIRES USER CONFIRMATION."""
    return users_mod.lock_user(username)


@tool
def unlock_user(username: str) -> dict:
    """Unlock a previously-locked user account. REQUIRES USER CONFIRMATION."""
    return users_mod.unlock_user(username)


@tool
def set_user_password(username: str, password: str) -> dict:
    """Set a user's password (chpasswd via stdin — never appears in argv).
"""
    return users_mod.set_password(username, password)


@tool
def service_action(name: str, action: str) -> dict:
    """Start, stop, restart, or reload a systemd .service unit on the host.
    `action` must be one of: start, stop, restart, reload.
"""
    if action not in {"start", "stop", "restart", "reload"}:
        return {"ok": False, "error": f"invalid action: {action}"}
    out = services_mod.action(name, action)
    return out.model_dump() if hasattr(out, "model_dump") else dict(out)


@tool
def apply_audit_fix(fix_id: str, evidence: dict | None = None) -> dict:
    """Apply the registered fix for a security finding. fix_id is the family
    prefix (e.g. 'ssh.permit_root_login') or the full finding id (with hash).
"""
    return _apply_fix(fix_id, evidence or {})


WRITE_TOOLS = [
    create_user, add_ssh_key, lock_user, unlock_user, set_user_password,
    service_action, apply_audit_fix,
]

DESTRUCTIVE_NAMES: set[str] = {
    "create_user", "add_ssh_key", "lock_user", "unlock_user", "set_user_password",
    "service_action", "apply_audit_fix",
}

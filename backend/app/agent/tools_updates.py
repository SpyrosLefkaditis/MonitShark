"""@tool wrappers around app.updates for the LangGraph agent."""
from __future__ import annotations

from langchain_core.tools import tool

from app import updates as upd


@tool
def updates_list() -> dict:
    """List pending OS package updates. Returns the package manager (apt/dnf/unknown)
    and the list of upgradable packages with current/new versions and a source field
    (``security`` for security-channel updates, the repo/dist name otherwise)."""
    pm = upd.detect_pm()
    pkgs = upd.list_upgradable()
    sec = [p for p in pkgs if p.get("is_security")]
    return {
        "package_manager": pm,
        "total": len(pkgs),
        "security_count": len(sec),
        "packages": pkgs,
    }


@tool
def updates_apply_security() -> dict:
    """Apply only security updates on the host. Long-running. May restart services
    silently. Destructive."""
    return upd.upgrade_security_only()


@tool
def updates_apply_all() -> dict:
    """Apply every pending update on the host. Long-running. Larger blast radius
    than security-only. Destructive."""
    return upd.upgrade_all()


TOOLS = [updates_list, updates_apply_security, updates_apply_all]

DESTRUCTIVE_NAMES = {"updates_apply_security", "updates_apply_all"}

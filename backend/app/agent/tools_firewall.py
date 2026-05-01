"""@tool wrappers around app.firewall for the LangGraph agent.

Read-only tools execute inline; the names listed in ``DESTRUCTIVE_NAMES`` are
gated by the confirmation node in the parent graph.
"""
from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import tool

from app import firewall as fw


def _err(e: Exception) -> dict[str, Any]:
    return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@tool
def firewall_status() -> dict:
    """Return the host firewall (UFW) status: active flag, default incoming/outgoing
    policies, and the current rule list. Returns ``{"installed": False}`` if ufw
    is not installed on the host."""
    try:
        return fw.status()
    except (fw.FirewallError, ValueError) as e:
        return _err(e)


@tool
def firewall_list_rules() -> list[dict]:
    """List the active UFW rules. Each rule: to, action (ALLOW/DENY/REJECT/LIMIT),
    from, proto (tcp|udp|None), comment."""
    try:
        return fw.list_rules()
    except (fw.FirewallError, ValueError):
        return []


@tool
def firewall_add_rule(
    action: Literal["allow", "deny", "reject", "limit"],
    port: int | str,
    proto: Literal["tcp", "udp"] | None = None,
    source: str | None = None,
    comment: str | None = None,
) -> dict:
    """Add a UFW rule. ``port`` may be a numeric port (1-65535) or a service name
    (e.g. ``"ssh"``, ``"apache2"``). ``proto`` is optional and defaults to all
    protocols. ``source`` may be ``None``/``"any"`` or a CIDR/IP. Destructive."""
    try:
        return fw.add_rule(action=action, port=port, proto=proto, source=source, comment=comment)
    except (fw.FirewallError, ValueError) as e:
        return _err(e)


@tool
def firewall_delete_rule(rule_number: int) -> dict:
    """Delete the UFW rule at the given 1-based position. Use ``firewall_list_rules``
    or ``firewall_status`` first to determine the target rule's number. Destructive."""
    try:
        return fw.delete_rule(rule_number=rule_number)
    except (fw.FirewallError, ValueError) as e:
        return _err(e)


@tool
def firewall_enable() -> dict:
    """Enable the host firewall (UFW). Existing connections may be impacted if
    the default-incoming policy is deny. Destructive."""
    try:
        return fw.enable()
    except (fw.FirewallError, ValueError) as e:
        return _err(e)


@tool
def firewall_disable() -> dict:
    """Disable the host firewall (UFW). The host will accept any inbound traffic
    not blocked elsewhere. Destructive."""
    try:
        return fw.disable()
    except (fw.FirewallError, ValueError) as e:
        return _err(e)


TOOLS = [
    firewall_status,
    firewall_list_rules,
    firewall_add_rule,
    firewall_delete_rule,
    firewall_enable,
    firewall_disable,
]

DESTRUCTIVE_NAMES = {
    "firewall_add_rule",
    "firewall_delete_rule",
    "firewall_enable",
    "firewall_disable",
}

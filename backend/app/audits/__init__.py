"""Audit registry. Each audit returns AuditReport(name, findings)."""
from __future__ import annotations

from typing import Awaitable, Callable

from app.schemas import AuditReport

# Each audit is async to allow shelling out without blocking the event loop.
AuditFn = Callable[[], Awaitable[AuditReport]]

REGISTRY: dict[str, AuditFn] = {}


def register(name: str):
    """Decorator: register an audit fn under `name` in the global registry."""
    def deco(fn: AuditFn) -> AuditFn:
        REGISTRY[name] = fn
        return fn
    return deco


# Imported at end so each audit module's @register call runs.
from app.audits import ssh as _ssh, users as _users, permissions as _permissions, packages as _packages  # noqa: E402,F401
